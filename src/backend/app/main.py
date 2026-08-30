from pathlib import Path
from collections import defaultdict
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from .database import get_connection
from .robot_state import router as robot_state_router
from .models import (
    AdminCommand,
    AdminCommandCreate,
    AdminCommandResult,
    AdminCommandStatus,
    ErrorCreate,
    ErrorLog,
    ErrorStats,
    Flavor,
    FlavorUpdate,
    FlavorSelection,
    Order,
    OrderCreate,
    OrderStats,
    OrderStatus,
    OrderStatusUpdate,
)

app = FastAPI(title="Robot Ice Cream API", version="1.0.0")
app.include_router(robot_state_router)
Db = Annotated[psycopg.Connection, Depends(get_connection)]
KIOSK_HTML = Path(__file__).resolve().parents[2] / "frontend" / "roskin_robbins_v5.html"



class RobotFeedback(BaseModel):
    status: OrderStatus = OrderStatus.PROCESSING
    step: str
    progress: int = Field(ge=0, le=100)
    message: str = ""
    eta_seconds: int | None = Field(default=None, ge=0)


order_sockets: dict[int, set[WebSocket]] = defaultdict(set)


async def broadcast_order_feedback(order_id: int, payload: dict):
    disconnected = []
    for websocket in order_sockets[order_id]:
        try:
            await websocket.send_json(payload)
        except Exception:
            disconnected.append(websocket)
    for websocket in disconnected:
        order_sockets[order_id].discard(websocket)


@app.websocket("/ws/orders/{order_id}")
async def order_feedback_socket(websocket: WebSocket, order_id: int):
    await websocket.accept()
    order_sockets[order_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        order_sockets[order_id].discard(websocket)


@app.post("/robot/orders/{order_id}/feedback")
async def receive_robot_feedback(order_id: int, body: RobotFeedback, db: Db):
    row = db.execute("SELECT status FROM order_history WHERE id = %s", (order_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 주문입니다.")
    should_save_status = (row["status"] == "PENDING" and body.status == OrderStatus.PROCESSING) or (row["status"] in ("PENDING", "PROCESSING") and body.status in (OrderStatus.COMPLETED, OrderStatus.FAILED))
    if should_save_status:
        db.execute("UPDATE order_history SET status = %s WHERE id = %s", (body.status.value, order_id))
    payload = {"order_id": order_id, **body.model_dump(mode="json")}
    await broadcast_order_feedback(order_id, payload)
    return payload


@app.get("/", include_in_schema=False)
@app.get("/kiosk", include_in_schema=False)
def kiosk() -> FileResponse:
    return FileResponse(KIOSK_HTML)


@app.get("/admin", include_in_schema=False)
def admin() -> RedirectResponse:
    return RedirectResponse("/kiosk#admin")


@app.get("/database", include_in_schema=False)
def database_page() -> RedirectResponse:
    return RedirectResponse("/kiosk#admin")


@app.get("/health")
def health(db: Db) -> dict[str, str]:
    db.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/flavors", response_model=list[Flavor])
def list_flavors(db: Db, available_only: bool = False):
    query = "SELECT id, name, name_en, description, description_en, is_available FROM icecream_flavor"
    if available_only:
        query += " WHERE is_available = TRUE"
    query += " ORDER BY id"
    return db.execute(query).fetchall()


@app.put("/flavors/selection", response_model=list[Flavor])
def update_flavor_selection(body: FlavorSelection, db: Db):
    selected_ids = list(dict.fromkeys(body.flavor_ids))
    if len(selected_ids) != 3:
        raise HTTPException(status_code=422, detail="서로 다른 맛을 정확히 3개 선택해야 합니다.")
    existing = db.execute(
        "SELECT id FROM icecream_flavor WHERE id = ANY(%s)", (selected_ids,)
    ).fetchall()
    if len(existing) != 3:
        raise HTTPException(status_code=404, detail="존재하지 않는 맛이 포함되어 있습니다.")
    db.execute(
        "UPDATE icecream_flavor SET is_available = (id = ANY(%s))", (selected_ids,)
    )
    return db.execute(
        """SELECT id, name, name_en, description, description_en, is_available
           FROM icecream_flavor WHERE is_available = TRUE ORDER BY id"""
    ).fetchall()


@app.patch("/flavors/{flavor_id}", response_model=Flavor)
def update_flavor(flavor_id: int, body: FlavorUpdate, db: Db):
    try:
        row = db.execute(
            """UPDATE icecream_flavor
               SET name = COALESCE(%s, name),
                   name_en = COALESCE(%s, name_en),
                   description = COALESCE(%s, description),
                   description_en = COALESCE(%s, description_en),
                   is_available = COALESCE(%s, is_available)
               WHERE id = %s
               RETURNING id, name, name_en, description, description_en, is_available""",
            (body.name, body.name_en, body.description, body.description_en, body.is_available, flavor_id),
        ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="이미 사용 중인 맛 이름입니다.") from None
    if row is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 맛입니다.")
    return row


@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(body: OrderCreate, db: Db):
    row = db.execute(
        """INSERT INTO order_history (flavor_id)
           SELECT id FROM icecream_flavor WHERE id = %s AND is_available = TRUE
           RETURNING id, flavor_id, status, ordered_at""",
        (body.flavor_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=409, detail="존재하지 않거나 판매할 수 없는 맛입니다.")
    flavor = db.execute(
        "SELECT name FROM icecream_flavor WHERE id = %s", (body.flavor_id,)
    ).fetchone()
    return {**row, "flavor_name": flavor["name"]}


@app.get("/orders/stats", response_model=OrderStats)
def order_stats(db: Db):
    totals = db.execute(
        """SELECT COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE status = 'PENDING') AS pending,
                  COUNT(*) FILTER (WHERE status = 'PROCESSING') AS processing,
                  COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed,
                  COUNT(*) FILTER (WHERE status = 'FAILED') AS failed
           FROM order_history"""
    ).fetchone()
    flavors = db.execute(
        """SELECT f.name, COUNT(o.id) AS count
           FROM icecream_flavor f LEFT JOIN order_history o ON o.flavor_id = f.id
           GROUP BY f.id, f.name ORDER BY count DESC, f.id"""
    ).fetchall()
    return {**totals, "by_flavor": flavors}


@app.get("/robot/orders/next", response_model=Order | None)
def get_next_robot_order(db: Db):
    return db.execute(
        """SELECT o.id, o.flavor_id, f.name AS flavor_name, o.status, o.ordered_at
           FROM order_history o JOIN icecream_flavor f ON f.id = o.flavor_id
           WHERE o.status = 'PENDING'
           ORDER BY o.ordered_at, o.id LIMIT 1"""
    ).fetchone()


@app.post("/robot/orders/{order_id}/claim", response_model=Order)
def claim_robot_order(order_id: int, db: Db):
    row = db.execute(
        """UPDATE order_history o SET status = 'PROCESSING'
           FROM icecream_flavor f
           WHERE o.id = %s AND o.status = 'PENDING' AND f.id = o.flavor_id
           RETURNING o.id, o.flavor_id, f.name AS flavor_name, o.status, o.ordered_at""",
        (order_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="존재하지 않거나 이미 다른 로봇이 수령한 주문입니다.",
        )
    return row


@app.get("/orders", response_model=list[Order])
def list_orders(
    db: Db,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return db.execute(
        """SELECT o.id, o.flavor_id, f.name AS flavor_name, o.status, o.ordered_at
           FROM order_history o JOIN icecream_flavor f ON f.id = o.flavor_id
           ORDER BY o.ordered_at DESC, o.id DESC LIMIT %s OFFSET %s""",
        (limit, offset),
    ).fetchall()


@app.patch("/orders/{order_id}/status", response_model=Order)
def update_order_status(order_id: int, body: OrderStatusUpdate, db: Db):
    row = db.execute(
        """UPDATE order_history o SET status = %s
           FROM icecream_flavor f
           WHERE o.id = %s AND f.id = o.flavor_id
           RETURNING o.id, o.flavor_id, f.name AS flavor_name, o.status, o.ordered_at""",
        (body.status.value, order_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 주문입니다.")
    return row


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int, db: Db):
    row = db.execute(
        """SELECT o.id, o.flavor_id, f.name AS flavor_name, o.status, o.ordered_at
           FROM order_history o JOIN icecream_flavor f ON f.id = o.flavor_id
           WHERE o.id = %s""",
        (order_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 주문입니다.")
    return row


@app.post("/errors", response_model=ErrorLog, status_code=status.HTTP_201_CREATED)
def create_error(body: ErrorCreate, db: Db):
    try:
        row = db.execute(
            """INSERT INTO error_log (order_id, process_step, error_code, message)
               VALUES (%s, %s, %s, %s)
               RETURNING id, order_id, process_step, error_code, message, created_at""",
            (body.order_id, body.process_step.value, body.error_code.value, body.message),
        ).fetchone()
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(status_code=404, detail="존재하지 않는 주문입니다.") from None
    return row


@app.get("/errors/stats", response_model=ErrorStats)
def error_stats(db: Db):
    by_step = db.execute(
        "SELECT process_step AS name, COUNT(*) AS count FROM error_log GROUP BY process_step ORDER BY count DESC"
    ).fetchall()
    by_code = db.execute(
        "SELECT error_code AS name, COUNT(*) AS count FROM error_log GROUP BY error_code ORDER BY count DESC"
    ).fetchall()
    return {"by_step": by_step, "by_code": by_code}


@app.get("/errors", response_model=list[ErrorLog])
def list_errors(db: Db, limit: Annotated[int, Query(ge=1, le=500)] = 100):
    return db.execute(
        """SELECT id, order_id, process_step, error_code, message, created_at
           FROM error_log ORDER BY created_at DESC, id DESC LIMIT %s""",
        (limit,),
    ).fetchall()


@app.get("/errors/{order_id}", response_model=list[ErrorLog])
def list_order_errors(order_id: int, db: Db):
    return db.execute(
        """SELECT id, order_id, process_step, error_code, message, created_at
           FROM error_log WHERE order_id = %s ORDER BY created_at DESC, id DESC""",
        (order_id,),
    ).fetchall()


@app.post("/robot/admin/commands", response_model=AdminCommand, status_code=status.HTTP_201_CREATED)
def create_admin_command(body: AdminCommandCreate, db: Db):
    joints = body.joint_positions
    if body.command.value == "MOVE_JOINTS":
        if joints is None or len(joints) != 6 or any(value < -180 or value > 180 for value in joints):
            raise HTTPException(status_code=422, detail="MOVE_JOINTS는 -180~180도 범위의 관절값 6개가 필요합니다.")
    elif joints is not None:
        raise HTTPException(status_code=422, detail="관절값은 MOVE_JOINTS 명령에만 사용할 수 있습니다.")

    unfinished = db.execute(
        "SELECT id FROM admin_command WHERE status IN ('PENDING', 'PROCESSING') LIMIT 1"
    ).fetchone()
    if unfinished is not None:
        raise HTTPException(status_code=409, detail=f"관리자 명령 #{unfinished['id']} 처리 중입니다.")

    return db.execute(
        """INSERT INTO admin_command (command, joint_positions)
           VALUES (%s, %s)
           RETURNING id, command, joint_positions, status, message,
                     created_at, started_at, completed_at""",
        (body.command.value, joints),
    ).fetchone()


@app.get("/robot/admin/commands/next", response_model=AdminCommand | None)
def get_next_admin_command(db: Db):
    return db.execute(
        """SELECT id, command, joint_positions, status, message,
                  created_at, started_at, completed_at
           FROM admin_command WHERE status = 'PENDING'
           ORDER BY created_at, id LIMIT 1"""
    ).fetchone()


@app.post("/robot/admin/commands/{command_id}/claim", response_model=AdminCommand)
def claim_admin_command(command_id: int, db: Db):
    row = db.execute(
        """UPDATE admin_command SET status = 'PROCESSING', started_at = CURRENT_TIMESTAMP
           WHERE id = %s AND status = 'PENDING'
           RETURNING id, command, joint_positions, status, message,
                     created_at, started_at, completed_at""",
        (command_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=409, detail="존재하지 않거나 이미 처리 중인 관리자 명령입니다.")
    return row


@app.patch("/robot/admin/commands/{command_id}/result", response_model=AdminCommand)
def finish_admin_command(command_id: int, body: AdminCommandResult, db: Db):
    if body.status not in (AdminCommandStatus.SUCCEEDED, AdminCommandStatus.FAILED):
        raise HTTPException(status_code=422, detail="결과 상태는 SUCCEEDED 또는 FAILED여야 합니다.")
    row = db.execute(
        """UPDATE admin_command
           SET status = %s, message = %s, completed_at = CURRENT_TIMESTAMP
           WHERE id = %s AND status = 'PROCESSING'
           RETURNING id, command, joint_positions, status, message,
                     created_at, started_at, completed_at""",
        (body.status.value, body.message, command_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=409, detail="처리 중인 관리자 명령이 아닙니다.")
    return row


@app.get("/robot/admin/commands/{command_id}", response_model=AdminCommand)
def get_admin_command(command_id: int, db: Db):
    row = db.execute(
        """SELECT id, command, joint_positions, status, message,
                  created_at, started_at, completed_at
           FROM admin_command WHERE id = %s""",
        (command_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 관리자 명령입니다.")
    return row

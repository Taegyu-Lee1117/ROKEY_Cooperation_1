from pathlib import Path
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

from .database import get_connection
from .models import (
    ErrorCreate,
    ErrorLog,
    ErrorStats,
    Flavor,
    FlavorAvailability,
    Order,
    OrderCreate,
    OrderStats,
    OrderStatusUpdate,
)

app = FastAPI(title="Robot Ice Cream API", version="1.0.0")
Db = Annotated[psycopg.Connection, Depends(get_connection)]
KIOSK_HTML = Path(__file__).resolve().parents[2] / "ui_preview" / "index.html"
ADMIN_HTML = Path(__file__).resolve().parents[2] / "ui_preview" / "admin.html"
DATABASE_HTML = Path(__file__).resolve().parents[2] / "ui_preview" / "database.html"


@app.get("/", include_in_schema=False)
@app.get("/kiosk", include_in_schema=False)
def kiosk() -> FileResponse:
    return FileResponse(KIOSK_HTML)


@app.get("/admin", include_in_schema=False)
def admin() -> FileResponse:
    return FileResponse(ADMIN_HTML)


@app.get("/database", include_in_schema=False)
def database_page() -> FileResponse:
    return FileResponse(DATABASE_HTML)


@app.get("/health")
def health(db: Db) -> dict[str, str]:
    db.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/flavors", response_model=list[Flavor])
def list_flavors(db: Db, available_only: bool = False):
    query = "SELECT id, name, is_available FROM icecream_flavor"
    if available_only:
        query += " WHERE is_available = TRUE"
    query += " ORDER BY id"
    return db.execute(query).fetchall()


@app.patch("/flavors/{flavor_id}", response_model=Flavor)
def update_flavor(flavor_id: int, body: FlavorAvailability, db: Db):
    row = db.execute(
        """UPDATE icecream_flavor SET is_available = %s WHERE id = %s
           RETURNING id, name, is_available""",
        (body.is_available, flavor_id),
    ).fetchone()
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

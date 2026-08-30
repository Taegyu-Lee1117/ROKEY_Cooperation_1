"""단일 로봇의 준비/작업/복귀/오류 상태 API."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .database import get_connection

router = APIRouter()
Db = Annotated[psycopg.Connection, Depends(get_connection)]


class RobotStatus(StrEnum):
    IDLE = "IDLE"
    READY = "READY"
    PROCESSING = "PROCESSING"
    RETURNING_HOME = "RETURNING_HOME"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class RobotStateUpdate(BaseModel):
    status: RobotStatus
    current_order_id: int | None = None
    current_step: str = Field(default="", max_length=50)
    message: str = Field(default="", max_length=255)


class RobotState(RobotStateUpdate):
    updated_at: datetime


@router.get("/robot/state", response_model=RobotState)
def get_robot_state(db: Db):
    return db.execute(
        """SELECT status, current_order_id, current_step, message, updated_at
           FROM robot_state WHERE id = 1"""
    ).fetchone()


@router.patch("/robot/state", response_model=RobotState)
def update_robot_state(body: RobotStateUpdate, db: Db):
    return db.execute(
        """INSERT INTO robot_state
               (id, status, current_order_id, current_step, message, updated_at)
           VALUES (1, %s, %s, %s, %s, CURRENT_TIMESTAMP)
           ON CONFLICT (id) DO UPDATE SET
               status = EXCLUDED.status,
               current_order_id = EXCLUDED.current_order_id,
               current_step = EXCLUDED.current_step,
               message = EXCLUDED.message,
               updated_at = CURRENT_TIMESTAMP
           RETURNING status, current_order_id, current_step, message, updated_at""",
        (body.status.value, body.current_order_id, body.current_step, body.message),
    ).fetchone()


from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessStep(StrEnum):
    CUP_PICK = "CUP_PICK"
    CUP_PLACE = "CUP_PLACE"
    SCOOP_PICK = "SCOOP_PICK"
    MOVE_TO_ICECREAM = "MOVE_TO_ICECREAM"
    SCOOP_ICECREAM = "SCOOP_ICECREAM"
    PUT_ICECREAM_IN_CUP = "PUT_ICECREAM_IN_CUP"
    SCOOP_RETURN = "SCOOP_RETURN"
    SPOON_INSERT = "SPOON_INSERT"
    SERVE_CUP = "SERVE_CUP"


class ErrorCode(StrEnum):
    GRIP_FAILED = "GRIP_FAILED"
    MOVE_FAILED = "MOVE_FAILED"
    SCOOP_FAILED = "SCOOP_FAILED"
    INSERT_FAILED = "INSERT_FAILED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class Flavor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_available: bool


class FlavorAvailability(BaseModel):
    is_available: bool


class OrderCreate(BaseModel):
    flavor_id: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class Order(BaseModel):
    id: int
    flavor_id: int
    flavor_name: str
    status: OrderStatus
    ordered_at: datetime


class ErrorCreate(BaseModel):
    order_id: int
    process_step: ProcessStep
    error_code: ErrorCode
    message: str = Field(min_length=1, max_length=255)


class ErrorLog(BaseModel):
    id: int
    order_id: int
    process_step: ProcessStep
    error_code: ErrorCode
    message: str
    created_at: datetime


class CountByName(BaseModel):
    name: str
    count: int


class OrderStats(BaseModel):
    total: int
    pending: int
    processing: int
    completed: int
    failed: int
    by_flavor: list[CountByName]


class ErrorStats(BaseModel):
    by_step: list[CountByName]
    by_code: list[CountByName]

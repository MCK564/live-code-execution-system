from pydantic import BaseModel, ConfigDict
from datetime import datetime
from schemas.pagination import Pagination

EXECUTION_TIME_LIMIT = 10 #seconds

class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    execution_id: str
    status: str


class ExecutionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    execution_id: str
    status: str
    stdout: str
    stderr: str
    execution_time_ms: int | None = None
    queued_at: datetime | None = None
    running_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    timeout_at: datetime | None = None


class ExecutionHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id : str
    items : list[ExecutionResultResponse] | None = None
    pagination: Pagination | None = None



class ExecutionCancelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    execution_id: str
    status: str
    message: str | None = None

class ExecutionRetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    old_execution_id: str
    new_execution_id: str
    status: str
    message: str | None = None


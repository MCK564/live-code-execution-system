from pydantic import BaseModel, ConfigDict
from datetime import datetime

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
    execution_time_ms: int | None
    queued_at: datetime | None = None
    running_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    timeout_at: datetime | None = None

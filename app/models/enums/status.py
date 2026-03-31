from enum import Enum


class ExecutionStatus(Enum):
    QUEUED = "QUEUED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"



class SessionStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"



from fastapi import Query
from dataclasses import dataclass

@dataclass
class PaginationParams:
    page: int = Query(default=1, ge=1, descrition="Page number")
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page")
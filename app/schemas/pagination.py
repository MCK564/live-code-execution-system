from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

class PaginationResponse(BaseModel, Generic[T]):
    items : list[T]
    pagination: Pagination
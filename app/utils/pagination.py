from sqlalchemy.orm import Session
from sqlalchemy import func

from schemas.pagination import Pagination


def pagainate(query, page: int, page_size:int):
    total = query.order_by(None).with_entities(func.count()).scalar()
    items = query.offset((page-1) * page_size).limit(page_size).all()
    total_pages = (total+page_size-1) // page_size # ceiling division

    return items, Pagination(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages
    )
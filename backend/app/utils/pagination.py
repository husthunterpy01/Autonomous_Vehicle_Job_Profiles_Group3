from __future__ import annotations

from typing import TypeVar, Generic, List, Sequence

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy.orm import Query as SAQuery


T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @staticmethod
    def pagination_params(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    ):
        return {
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def paginate(
        query: SAQuery,
        page: int,
        page_size: int,
    ) -> PageResponse:
        total = query.count()

        items = (
            query
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        total_pages = (total + page_size - 1) // page_size

        return PageResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def paginate_list(
        data: Sequence[T],
        page: int,
        page_size: int,
    ) -> PageResponse[T]:
        total = len(data)

        start = (page - 1) * page_size
        items = list(data[start:start + page_size])

        total_pages = (total + page_size - 1) // page_size

        return PageResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
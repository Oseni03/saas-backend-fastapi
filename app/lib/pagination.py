"""
Pagination utilities — offset-based with consistent response envelope.

Usage in a route:
    @router.get("", response_model=PagedResponse[UserResponse])
    async def list_users(
        pagination: PaginationDep,
        db: DBDep,
    ) -> PagedResponse[UserResponse]:
        ...
"""

from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel

from app.config import project

T = TypeVar("T")


class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def build(cls, items: list[T], total: int, limit: int, offset: int) -> "PagedResponse[T]":
        return cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items)) < total,
        )


class PaginationParams:
    def __init__(
        self,
        limit: int = Query(default=project.pagination.default_limit, ge=1, le=project.pagination.max_limit, description="Items per page"),
        offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    ) -> None:
        self.limit = limit
        self.offset = offset


PaginationDep = Annotated[PaginationParams, Depends(PaginationParams)]

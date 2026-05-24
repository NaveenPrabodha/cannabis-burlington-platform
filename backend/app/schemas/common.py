from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(..., description="Total matching rows across all pages")
    page: int = Field(..., ge=1, description="Current page (1-indexed)")
    page_size: int = Field(..., ge=1, le=200)
    has_next: bool

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    db_ok: bool
    version: str
    env: str


class CountedItem(BaseModel):
    """Used by /categories and /brands — `name` is the value, `count` the # of products in it."""

    name: str
    count: int

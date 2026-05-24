from dataclasses import dataclass
from typing import Annotated

from fastapi import Query


@dataclass
class PaginationParams:
    page: int = 1
    page_size: int = 24

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    def build_response(self, items: list, total: int) -> dict:
        return {
            "items": items,
            "total": total,
            "page": self.page,
            "page_size": self.page_size,
            "has_next": self.offset + len(items) < total,
        }


def pagination_dep(
    page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page (max 100)")] = 24,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)

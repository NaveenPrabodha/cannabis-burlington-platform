from pydantic import BaseModel

from app.schemas.product import ProductWithMarketPrices
from app.schemas.store import StoreSummary


class SearchResults(BaseModel):
    query: str
    products: list[ProductWithMarketPrices]
    stores: list[StoreSummary]
    total_products: int
    total_stores: int

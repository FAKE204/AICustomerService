from typing import List

from pydantic import BaseModel, Field


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    highlights: List[str] = Field(default_factory=list)
    inventory: int = 0

from typing import List, Optional

from backend.app.schemas.product import Product


class ProductService:
    _products = [
        Product(
            product_id="P1001",
            name="智能空气炸锅",
            category="家电",
            price=399.0,
            highlights=["8L大容量", "可视化烹饪", "支持预约"],
            inventory=53,
        ),
        Product(
            product_id="P1002",
            name="降噪蓝牙耳机",
            category="数码",
            price=299.0,
            highlights=["主动降噪", "40小时续航", "双设备连接"],
            inventory=126,
        ),
        Product(
            product_id="P1003",
            name="保温咖啡杯",
            category="家居",
            price=89.0,
            highlights=["316不锈钢", "6小时保温", "防漏设计"],
            inventory=200,
        ),
    ]

    def __init__(self):
        pass

    async def list_products(self) -> List[Product]:
        return self.__class__._products

    async def get_product(self, product_id: str) -> Optional[Product]:
        for product in self.__class__._products:
            if product.product_id == product_id:
                return product
        return None

    async def search_products(self, keyword: str) -> List[Product]:
        normalized = keyword.strip().lower()
        if not normalized:
            return self.__class__._products

        results = []
        for product in self.__class__._products:
            haystack = " ".join(
                [product.name, product.category, " ".join(product.highlights)]
            ).lower()
            if normalized in haystack:
                results.append(product)
        return results

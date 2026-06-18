from fastapi import APIRouter

from backend.app.services.knowledge_service import KnowledgeService
from backend.app.services.order_service import OrderService
from backend.app.services.product_service import ProductService

router = APIRouter()
knowledge_service = KnowledgeService()
order_service = OrderService()
product_service = ProductService()


@router.get("/overview")
async def overview():
    documents = await knowledge_service.list_documents()
    orders = await order_service.list_orders()
    products = await product_service.list_products()
    refunding_count = len([order for order in orders if order.status == "refunding"])

    return {
        "knowledge_count": len(documents),
        "order_count": len(orders),
        "product_count": len(products),
        "refunding_count": refunding_count,
    }

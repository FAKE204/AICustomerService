from fastapi import APIRouter, HTTPException

from backend.app.schemas.order import RefundRequest
from backend.app.services.order_service import OrderService

router = APIRouter()
order_service = OrderService()


@router.get("")
async def list_orders():
    return await order_service.list_orders()


@router.get("/{order_no}")
async def get_order(order_no: str):
    order = await order_service.get_order(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.post("/refund")
async def request_refund(payload: RefundRequest):
    result = await order_service.request_refund(payload.order_no, payload.reason)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result

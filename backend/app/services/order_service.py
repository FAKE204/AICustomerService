from typing import List, Optional

from backend.app.schemas.order import Order


class OrderService:
    _orders = [
        Order(
            order_no="ORDER20240615001",
            user_name="张三",
            status="paid",
            amount=399.0,
            logistics_status="已发货，预计明日送达",
        ),
        Order(
            order_no="ORDER20240615002",
            user_name="李四",
            status="delivered",
            amount=299.0,
            logistics_status="已签收",
        ),
    ]

    def __init__(self):
        pass

    async def list_orders(self) -> List[Order]:
        return self.__class__._orders

    async def get_order(self, order_no: str) -> Optional[Order]:
        target = order_no.strip().upper()
        for order in self.__class__._orders:
            if order.order_no.upper() == target:
                return order
        return None

    async def request_refund(self, order_no: str, reason: str) -> dict:
        order = await self.get_order(order_no)
        if not order:
            return {
                "success": False,
                "message": f"未找到订单 {order_no}，请确认订单号后再试。",
            }

        if order.status == "refunding":
            return {"success": True, "message": f"订单 {order.order_no} 已在退款处理中。"}

        order.status = "refunding"
        return {
            "success": True,
            "message": f"订单 {order.order_no} 已提交退款申请，原因：{reason}。",
        }

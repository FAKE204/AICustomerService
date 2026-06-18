from pydantic import BaseModel


class Order(BaseModel):
    order_no: str
    user_name: str
    status: str
    amount: float
    logistics_status: str


class RefundRequest(BaseModel):
    order_no: str
    reason: str

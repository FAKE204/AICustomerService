from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.schemas.intent import IntentResult
from backend.app.services.agent_service import AgentService
from backend.app.services.llm_service import LLMService
from backend.app.services.order_service import OrderService
from backend.app.services.product_service import ProductService
from backend.app.services.rag_service import RAGService


class ChatService:
    def __init__(self):
        self.agent_service = AgentService()
        self.llm_service = LLMService()
        self.order_service = OrderService()
        self.product_service = ProductService()
        self.rag_service = RAGService()

    async def chat(self, payload: ChatRequest) -> ChatResponse:
        agent_result = await self.agent_service.analyze(payload.message)
        intent = agent_result["intent"]
        answer, metadata = await self._dispatch(payload.message, intent)

        return ChatResponse(
            session_id=payload.session_id,
            answer=answer,
            intent=intent,
            sentiment=agent_result["sentiment"],
            confidence=intent.confidence,
            metadata=metadata,
        )

    async def _dispatch(self, message: str, intent: IntentResult) -> tuple[str, dict]:
        if intent.intent_code == "order_query":
            order_no = next(
                (entity.value for entity in intent.entities if entity.type == "order_no"),
                "",
            )
            if order_no:
                order = await self.order_service.get_order(order_no)
                if order:
                    return (
                        f"订单 {order.order_no} 当前状态为 {order.status}，物流信息：{order.logistics_status}。",
                        {"source": "order_service", "order_no": order.order_no},
                    )
            return (
                "请提供完整订单号，我可以帮您查询订单状态和物流进度。",
                {"source": "order_service"},
            )

        if intent.intent_code == "refund_request":
            order_no = next(
                (entity.value for entity in intent.entities if entity.type == "order_no"),
                "",
            )
            if order_no:
                result = await self.order_service.request_refund(order_no, "用户主动申请")
                return result["message"], {"source": "order_service", "order_no": order_no}
            return (
                "可以为您发起退款申请，请先提供订单号，并说明退款原因。",
                {"source": "order_service"},
            )

        if intent.intent_code == "product_inquiry":
            products = await self.product_service.search_products(message)
            if products:
                product = products[0]
                answer = (
                    f"为您找到商品 {product.name}，价格 {product.price:.2f} 元，"
                    f"亮点包括：{'、'.join(product.highlights)}。"
                )
                return answer, {"source": "product_service", "product_id": product.product_id}

            context = await self.rag_service.retrieve(message, top_k=3)
            answer = await self.rag_service.generate(message, context)
            return answer, {"source": "rag_service"}

        if intent.intent_code in {"complaint", "human_agent"}:
            return (
                "已为您识别到需要人工协助，我建议尽快转人工客服继续处理。",
                {"source": "agent_service", "transfer": True},
            )

        prompt = (
            "你是电商智能客服，请用简洁、专业、友好的方式回答用户问题。\n"
            f"用户问题：{message}"
        )
        answer = await self.llm_service.generate(prompt)
        return answer, {"source": "llm_service"}

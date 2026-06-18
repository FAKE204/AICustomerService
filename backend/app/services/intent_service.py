import json
import logging
import re
from typing import Dict, List, Optional

from backend.app.schemas.intent import Entity, IntentResult
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class IntentService:
    INTENT_CONFIGS: Dict[str, Dict[str, object]] = {
        "product_inquiry": {
            "name": "商品咨询",
            "keywords": ["商品", "产品", "多少钱", "价格", "怎么样", "好不好"],
            "handler": "rag",
            "priority": 5,
            "examples": ["这个商品多少钱", "这款产品怎么样"],
        },
        "order_query": {
            "name": "订单查询",
            "keywords": ["订单", "查订单", "什么时候到", "发货没", "物流"],
            "handler": "tool",
            "priority": 8,
            "examples": ["帮我查一下订单", "订单什么时候发货"],
        },
        "refund_request": {
            "name": "退款申请",
            "keywords": ["退款", "退货", "取消订单", "不想要了"],
            "handler": "tool",
            "priority": 10,
            "examples": ["我要退款", "帮我退货"],
        },
        "complaint": {
            "name": "投诉反馈",
            "keywords": ["投诉", "差评", "太差了", "骗子", "态度差"],
            "handler": "transfer",
            "priority": 10,
            "examples": ["我要投诉", "你们服务太差了"],
        },
        "human_agent": {
            "name": "转人工",
            "keywords": ["人工", "客服", "真人", "转人工", "人工服务"],
            "handler": "transfer",
            "priority": 10,
            "examples": ["帮我转人工", "我要真人客服"],
        },
        "greeting": {
            "name": "问候",
            "keywords": ["你好", "您好", "hi", "hello", "在吗"],
            "handler": "llm",
            "priority": 1,
            "examples": ["你好", "在吗"],
        },
        "fallback": {
            "name": "其他",
            "keywords": [],
            "handler": "llm",
            "priority": 0,
            "examples": [],
        },
    }

    def __init__(self):
        self.llm_service = LLMService()
        self.embedding_service = EmbeddingService()

    async def recognize(self, message: str) -> IntentResult:
        text = message.strip()
        logger.info("开始识别用户意图: %s", text)

        keyword_intent = self._keyword_match(text)
        semantic_intent = await self._semantic_match(text)
        llm_intent = await self._llm_understand(text)
        final_intent = self._fuse_intents(keyword_intent, semantic_intent, llm_intent)
        final_intent.entities = await self._extract_entities(text, final_intent.intent_code)

        logger.info("意图识别完成: %s", final_intent.intent_code)
        return final_intent

    def _build_result(self, intent_code: str, confidence: float) -> IntentResult:
        config = self.INTENT_CONFIGS[intent_code]
        return IntentResult(
            intent_code=intent_code,
            intent_name=str(config["name"]),
            confidence=max(0.0, min(1.0, confidence)),
            entities=[],
            handler_type=str(config["handler"]),
            priority=int(config["priority"]),
        )

    def _keyword_match(self, text: str) -> Optional[IntentResult]:
        text_lower = text.lower()
        for intent_code, config in self.INTENT_CONFIGS.items():
            keywords = config.get("keywords", [])
            if any(keyword.lower() in text_lower for keyword in keywords):
                return self._build_result(intent_code, 0.78)
        return None

    async def _semantic_match(self, text: str) -> Optional[IntentResult]:
        text_vector = (await self.embedding_service.encode([text]))[0]
        best_code = None
        best_score = 0.0

        for intent_code, config in self.INTENT_CONFIGS.items():
            examples = config.get("examples", [])
            if not examples:
                continue

            example_vectors = await self.embedding_service.encode(list(examples))
            scores = [
                self.embedding_service.cosine_similarity(text_vector, example_vector)
                for example_vector in example_vectors
            ]
            score = max(scores) if scores else 0.0
            if score > best_score:
                best_score = score
                best_code = intent_code

        if best_code and best_score >= 0.72:
            return self._build_result(best_code, round(best_score, 3))
        return None

    async def _llm_understand(self, text: str) -> Optional[IntentResult]:
        prompt = (
            "请分析以下电商客服用户输入的意图，只返回 JSON。\n"
            f"用户输入：{text}\n"
            "可选意图：product_inquiry, order_query, refund_request, complaint, "
            "human_agent, greeting, fallback\n"
            '格式：{"intent_code":"xxx","confidence":0.0}'
        )

        try:
            response = await self.llm_service.generate(prompt, temperature=0.1, max_tokens=128)
            result = json.loads(response)
            intent_code = result.get("intent_code", "fallback")
            if intent_code not in self.INTENT_CONFIGS:
                intent_code = "fallback"
            confidence = float(result.get("confidence", 0.55))
            return self._build_result(intent_code, confidence)
        except Exception as exc:
            logger.warning("LLM 意图理解失败，已忽略该结果: %s", exc)
            return None

    def _fuse_intents(self, *intents: Optional[IntentResult]) -> IntentResult:
        valid_intents = [intent for intent in intents if intent is not None]
        if not valid_intents:
            return self._build_result("fallback", 0.5)
        return max(valid_intents, key=lambda item: item.confidence * max(item.priority, 1))

    async def _extract_entities(self, text: str, intent_code: str) -> List[Entity]:
        del intent_code
        entities: List[Entity] = []

        for match in re.finditer(r"ORDER[\w]{8,}", text.upper()):
            entities.append(
                Entity(type="order_no", value=match.group(), start=match.start(), end=match.end())
            )

        for match in re.finditer(r"1[3-9]\d{9}", text):
            entities.append(
                Entity(type="phone", value=match.group(), start=match.start(), end=match.end())
            )

        return entities

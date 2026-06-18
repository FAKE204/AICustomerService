from typing import Dict

from backend.app.services.intent_service import IntentService
from backend.app.services.sentiment_service import SentimentService


class AgentService:
    def __init__(self):
        self.intent_service = IntentService()
        self.sentiment_service = SentimentService()

    async def analyze(self, message: str) -> Dict[str, object]:
        intent = await self.intent_service.recognize(message)
        sentiment, score = await self.sentiment_service.analyze(message)
        strategy = self.sentiment_service.get_response_strategy(sentiment, score)

        return {
            "intent": intent,
            "sentiment": sentiment.value,
            "sentiment_score": round(score, 3),
            "handler": intent.handler_type,
            "strategy": strategy,
        }

from backend.app.schemas.conversation import (
    ConversationMessage,
    ConversationRequest,
    ConversationResponse,
)
from backend.app.services.llm_service import LLMService


class ConversationService:
    def __init__(self):
        self.llm_service = LLMService()

    async def chat(self, payload: ConversationRequest) -> ConversationResponse:
        messages = self._build_messages(payload)
        answer = await self.llm_service.chat(
            [message.model_dump() for message in messages],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )

        updated_messages = [
            *messages,
            ConversationMessage(role="assistant", content=answer),
        ]

        return ConversationResponse(
            session_id=payload.session_id,
            answer=answer,
            messages=updated_messages,
            metadata={
                "source": "llm_service",
                "turn_count": len(updated_messages),
            },
        )

    def _build_messages(self, payload: ConversationRequest) -> list[ConversationMessage]:
        messages: list[ConversationMessage] = []
        if payload.system_prompt:
            messages.append(
                ConversationMessage(role="system", content=payload.system_prompt)
            )

        messages.extend(payload.history)
        messages.append(ConversationMessage(role="user", content=payload.message))
        return messages

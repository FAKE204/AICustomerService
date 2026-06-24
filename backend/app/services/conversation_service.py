import json
from typing import AsyncIterator

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

        return self._build_response(payload, messages, answer)

    async def stream_chat(self, payload: ConversationRequest) -> AsyncIterator[str]:
        messages = self._build_messages(payload)
        answer_parts: list[str] = []

        try:
            async for chunk in self.llm_service.stream_chat(
                [message.model_dump() for message in messages],
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            ):
                answer_parts.append(chunk)
                yield self._format_sse("delta", {"content": chunk})
        except Exception as exc:
            yield self._format_sse("error", {"message": str(exc) or "流式输出失败"})
            return

        response = self._build_response(payload, messages, "".join(answer_parts))
        yield self._format_sse("done", response.model_dump())

    def _build_response(
        self,
        payload: ConversationRequest,
        messages: list[ConversationMessage],
        answer: str,
    ) -> ConversationResponse:
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

    def _format_sse(self, event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _build_messages(self, payload: ConversationRequest) -> list[ConversationMessage]:
        messages: list[ConversationMessage] = []
        if payload.system_prompt:
            messages.append(
                ConversationMessage(role="system", content=payload.system_prompt)
            )

        messages.extend(payload.history)
        messages.append(ConversationMessage(role="user", content=payload.message))
        return messages

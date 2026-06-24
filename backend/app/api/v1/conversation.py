from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.app.schemas.conversation import ConversationRequest, ConversationResponse
from backend.app.services.conversation_service import ConversationService

router = APIRouter()
conversation_service = ConversationService()


@router.post("", response_model=None)
async def create_conversation(
    payload: ConversationRequest,
) -> ConversationResponse | StreamingResponse:
    if payload.stream:
        return StreamingResponse(
            conversation_service.stream_chat(payload),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await conversation_service.chat(payload)

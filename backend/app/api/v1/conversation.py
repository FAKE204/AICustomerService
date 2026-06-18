from fastapi import APIRouter

from backend.app.schemas.conversation import ConversationRequest, ConversationResponse
from backend.app.services.conversation_service import ConversationService

router = APIRouter()
conversation_service = ConversationService()


@router.post("", response_model=ConversationResponse)
async def create_conversation(payload: ConversationRequest) -> ConversationResponse:
    return await conversation_service.chat(payload)

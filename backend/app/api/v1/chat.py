from fastapi import APIRouter

from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()


@router.post("", response_model=ChatResponse)
async def create_chat(payload: ChatRequest) -> ChatResponse:
    return await chat_service.chat(payload)

from fastapi import APIRouter, Query

from backend.app.services.intent_service import IntentService

router = APIRouter()
intent_service = IntentService()


@router.get("/recognize")
async def recognize_intent(message: str = Query(..., min_length=1)):
    return await intent_service.recognize(message)

from fastapi import APIRouter, Query

from backend.app.services.agent_service import AgentService

router = APIRouter()
agent_service = AgentService()


@router.get("/analyze")
async def analyze_message(message: str = Query(..., min_length=1)):
    return await agent_service.analyze(message)

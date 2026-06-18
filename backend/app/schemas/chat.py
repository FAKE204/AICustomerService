from typing import Dict, List

from pydantic import BaseModel, Field

from backend.app.schemas.intent import IntentResult


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = "default"
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    intent: IntentResult
    sentiment: str
    confidence: float
    metadata: Dict[str, object] = Field(default_factory=dict)

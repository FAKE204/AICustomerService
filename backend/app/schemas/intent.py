from typing import List

from pydantic import BaseModel, Field


class Entity(BaseModel):
    type: str
    value: str
    start: int = 0
    end: int = 0


class IntentResult(BaseModel):
    intent_code: str
    intent_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    entities: List[Entity] = Field(default_factory=list)
    handler_type: str
    priority: int = 0

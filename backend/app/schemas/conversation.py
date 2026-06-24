from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ConversationMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ConversationRequest(BaseModel):
    session_id: str = "default"
    message: str = Field(min_length=1)
    history: List[ConversationMessage] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    @model_validator(mode="after")
    def normalize_system_prompt(self) -> "ConversationRequest":
        if self.system_prompt is not None:
            self.system_prompt = self.system_prompt.strip() or None
        return self


class ConversationResponse(BaseModel):
    session_id: str
    answer: str
    messages: List[ConversationMessage]
    metadata: Dict[str, object] = Field(default_factory=dict)

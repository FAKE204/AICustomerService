from pydantic import BaseModel, Field


class KnowledgeDocumentCreate(BaseModel):
    category: str
    question: str
    answer: str


class KnowledgeDocument(KnowledgeDocumentCreate):
    id: str = Field(default="")
    score: float = 0.0

from fastapi import APIRouter, Query

from backend.app.schemas.knowledge import KnowledgeDocumentCreate
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.services.rag_service import RAGService

router = APIRouter()
knowledge_service = KnowledgeService()
rag_service = RAGService()


@router.get("")
async def list_documents():
    return await knowledge_service.list_documents()


@router.get("/search")
async def search_documents(query: str = Query(..., min_length=1), top_k: int = 5):
    return await knowledge_service.search(query, top_k=top_k)


@router.post("")
async def add_document(payload: KnowledgeDocumentCreate):
    return await knowledge_service.add_document(payload)


@router.get("/answer")
async def answer_with_rag(query: str = Query(..., min_length=1)):
    context = await rag_service.retrieve(query, top_k=3)
    answer = await rag_service.generate(query, context)
    return {"query": query, "context": context, "answer": answer}

from typing import Dict, List
from uuid import uuid4

from backend.app.schemas.knowledge import KnowledgeDocument, KnowledgeDocumentCreate
from backend.app.services.embedding_service import EmbeddingService


class KnowledgeService:
    _documents: List[Dict[str, object]] = [
        {
            "id": "kb-001",
            "category": "商品咨询",
            "question": "商品支持7天无理由退货吗",
            "answer": "支持，签收后7天内且商品保持完好可申请无理由退货。",
        },
        {
            "id": "kb-002",
            "category": "配送服务",
            "question": "订单一般多久发货",
            "answer": "现货商品通常会在24小时内发货，节假日会顺延。",
        },
        {
            "id": "kb-003",
            "category": "售后服务",
            "question": "退款多久可以到账",
            "answer": "退款审核通过后，原路退回一般需要1到5个工作日到账。",
        },
    ]

    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def list_documents(self) -> List[KnowledgeDocument]:
        return [KnowledgeDocument(**doc) for doc in self.__class__._documents]

    async def add_document(self, payload: KnowledgeDocumentCreate) -> KnowledgeDocument:
        document = payload.model_dump()
        document["id"] = f"kb-{uuid4().hex[:8]}"
        self.__class__._documents.append(document)
        return KnowledgeDocument(**document)

    async def search(self, query: str, top_k: int = 5) -> List[KnowledgeDocument]:
        if not query.strip():
            return []

        query_embedding = (await self.embedding_service.encode([query]))[0]
        results: List[KnowledgeDocument] = []

        for document in self.__class__._documents:
            doc_text = f"{document['question']} {document['answer']}"
            doc_embedding = (await self.embedding_service.encode([doc_text]))[0]
            score = self.embedding_service.cosine_similarity(query_embedding, doc_embedding)
            results.append(KnowledgeDocument(**document, score=round(score, 4)))

        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

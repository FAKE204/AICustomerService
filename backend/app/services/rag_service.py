from typing import Dict, List, Optional

from backend.app.schemas.knowledge import KnowledgeDocumentCreate
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.services.llm_service import LLMService


class RAGService:
    def __init__(self):
        self.llm_service = LLMService()
        self.knowledge_service = KnowledgeService()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, str]] = None,
    ) -> str:
        documents = await self.knowledge_service.search(query, top_k=top_k)
        if filter:
            category = filter.get("category")
            if category:
                documents = [doc for doc in documents if doc.category == category]
        return self._format_context(documents)

    def _format_context(self, results: List[object]) -> str:
        if not results:
            return ""

        parts = []
        for index, item in enumerate(results, start=1):
            parts.append(
                f"【文档 {index}】相似度 {item.score:.2f}\n"
                f"分类：{item.category}\n"
                f"问题：{item.question}\n"
                f"回答：{item.answer}"
            )
        return "\n\n".join(parts)

    async def generate(self, query: str, context: str) -> str:
        if not context:
            return "知识库中暂未检索到强相关内容，建议转人工客服进一步确认。"

        prompt = (
            "你是电商智能客服，请严格根据知识库内容回答。\n"
            f"知识库上下文：\n{context}\n"
            f"用户问题：{query}\n"
            "要求：直接回答，简洁专业；如果上下文不足，请明确说明。"
        )
        return await self.llm_service.generate(prompt)

    async def add_document(self, document: Dict[str, str]) -> str:
        payload = KnowledgeDocumentCreate(**document)
        record = await self.knowledge_service.add_document(payload)
        return record.id

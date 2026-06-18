import hashlib
from math import sqrt
from typing import Iterable, List


class EmbeddingService:
    """使用稳定哈希生成轻量向量，便于在本地环境做相似度计算。"""

    VECTOR_SIZE = 16

    async def encode(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_vector(text) for text in texts]

    def cosine_similarity(self, vector_a: Iterable[float], vector_b: Iterable[float]) -> float:
        a = list(vector_a)
        b = list(vector_b)
        numerator = sum(x * y for x, y in zip(a, b))
        denominator = sqrt(sum(x * x for x in a)) * sqrt(sum(y * y for y in b))
        if not denominator:
            return 0.0
        return numerator / denominator

    def _text_to_vector(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.VECTOR_SIZE

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for index in range(self.VECTOR_SIZE):
            byte = digest[index]
            values.append((byte / 255.0) * 2 - 1)
        return values

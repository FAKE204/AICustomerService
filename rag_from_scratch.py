"""
从零实现的 RAG（检索增强生成）生命周期演示
================================================

目标：不依赖任何重型开发框架（无 LangChain / LlamaIndex / 向量数据库），
仅用 Python 原生代码 + 基础库（numpy / openai），理清 RAG 完整生命周期：

    文档 -> 切片(Chunking) -> 向量化(Embedding) -> 存储(内存索引)
        -> 检索(Retrieval, Top-K 余弦相似度) -> 拼接 Prompt -> LLM 生成

运行：
    .venv/Scripts/python.exe rag_from_scratch.py

各阶段对应函数：
    1. load_document        读取 TXT 文档
    2. chunk_by_length      按字符长度切分（带重叠）
       chunk_by_paragraph   按段落切分
    3. embed                文本块 -> 向量（openai / sentence-transformers / 本地兜底）
    4. VectorStore          内存中存储向量与文本块
    5. retrieve             numpy 计算余弦相似度，返回 Top-K
    6. build_prompt         将检索结果拼接入 Prompt
    7. generate             调用 LLM 生成回答
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

# Windows 终端默认 GBK，强制 stdout 用 UTF-8，避免中文乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 复用项目已有的 LLM 配置（DeepSeek，OpenAI 兼容接口）
from backend.app.core.config import settings


# ============================================================
# 1. 文档加载
# ============================================================
def load_document(path: str, encoding: str = "utf-8") -> str:
    """读取 TXT 文档并返回纯文本。"""
    with open(path, "r", encoding=encoding) as f:
        return f.read()


# ============================================================
# 2. 文本切片（Chunking）
# ============================================================
def chunk_by_length(
    text: str, max_chars: int = 200, overlap: int = 50
) -> List[str]:
    """按固定字符长度切分，相邻块之间保留 overlap 个字符的上下文重叠。

    重叠的作用：避免把一个完整语义从中间切断，提升检索召回率。
    """
    if max_chars <= 0:
        raise ValueError("max_chars 必须为正数")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap 必须满足 0 <= overlap < max_chars")

    chunks: List[str] = []
    start = 0
    step = max_chars - overlap  # 每次前进的步长
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def chunk_by_paragraph(text: str, max_chars: int = 300) -> List[str]:
    """按段落切分；若单段过长则继续按长度二次切分，保证每块不超过 max_chars。"""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            chunks.append(para)
        else:
            # 段落过长，退化为按长度切分（不带重叠，保持段落边界）
            for i in range(0, len(para), max_chars):
                piece = para[i : i + max_chars].strip()
                if piece:
                    chunks.append(piece)
    return chunks


# ============================================================
# 3. 向量化（Embedding）
# ============================================================
# 向量化后端：默认本地兜底，开箱即跑；如需真实语义向量可切换为
# "openai" 或 "sentence-transformers"（见 embed() 实现）。
EMBED_BACKEND = os.getenv("RAG_EMBED_BACKEND", "openai")
# EMBED_BACKEND = os.getenv("RAG_EMBED_BACKEND", "hashing")
EMBED_DIM = 256  # 本地兜底向量的维度


def _embed_openai(texts: Sequence[str]) -> List[List[float]]:
    """使用 openai 库调用 OpenAI 兼容的 Embedding 接口。"""
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("EMBED_API_KEY", settings.TXT_EMBEDDINGS_API_KEY),
        base_url=os.getenv("EMBED_API_BASE", settings.TXT_EMBEDDINGS_API_BASE),
    )
    model = os.getenv("EMBED_MODEL", "text-embedding-v4")
    resp = client.embeddings.create(model=model, input=list(texts))

    return [d.embedding for d in resp.data]


def _embed_sentence_transformers(texts: Sequence[str]) -> List[List[float]]:
    """使用本地 sentence-transformers 模型生成向量（需 pip install sentence-transformers）。"""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(os.getenv("ST_MODEL", "all-MiniLM-L6-v2"))
    return model.encode(list(texts)).tolist()


def _hash_vector(text: str, dim: int = EMBED_DIM) -> List[float]:
    """本地兜底：基于字符 bigram + 哈希的确定性向量化。

    不依赖任何外部服务，保证脚本可离线运行。用字符 bigram（而非整词）作为
    基本单元，这样未分词的中文也能做部分匹配（如"退款"在 query 与文档中命中）。
    语义表达仍远弱于真实 Embedding 模型，仅用于演示流程；生产环境请切换到
    openai / sentence-transformers。
    """
    vec = [0.0] * dim
    normalized = text.lower()
    tokens = re.findall(r"\w+", normalized)  # 英文/数字按词
    # 中文按相邻两字（bigram）切分，捕捉局部语义
    bigrams = [
        normalized[i : i + 2]
        for i in range(len(normalized) - 1)
        if re.match(r"[一-龥]", normalized[i : i + 2])
    ]
    for unit in tokens + bigrams:
        idx = hash(unit) % dim
        vec[idx] += 1.0
    return vec


def _embed_hashing(texts: Sequence[str]) -> List[List[float]]:
    return [_hash_vector(t) for t in texts]


_EMBED_BACKENDS = {
    "openai": _embed_openai,
    "sentence-transformers": _embed_sentence_transformers,
    "hashing": _embed_hashing,
}


def embed(texts: Sequence[str]) -> List[List[float]]:
    """统一向量化入口：根据 EMBED_BACKEND 选择实现。"""
    backend = _EMBED_BACKENDS.get(EMBED_BACKEND)
    if backend is None:
        raise ValueError(f"未知向量化后端: {EMBED_BACKEND}")
    return backend(texts)


# ============================================================
# 4. 存储（内存向量库）
# ============================================================
@dataclass
class VectorStore:
    """极简内存向量库：保存文本块与其向量，提供 Top-K 检索。"""

    chunks: List[str] = field(default_factory=list)
    matrix: Optional[np.ndarray] = None  # 形状 (n, dim)

    def add(self, chunks: Sequence[str]) -> None:
        """对文本块向量化并存入。"""
        if not chunks:
            return
        vectors = embed(chunks)
        new_matrix = np.array(vectors, dtype=np.float64)
        if self.matrix is None:
            self.matrix = new_matrix
        else:
            self.matrix = np.vstack([self.matrix, new_matrix])
        self.chunks.extend(chunks)

    # ------------------------------------------------------------
    # 5. 检索（Retrieval）：numpy 计算余弦相似度
    # ------------------------------------------------------------
    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """返回与 query 最相关的 Top-K 个文本块及其相似度得分。"""
        if self.matrix is None or not self.chunks:
            return []

        q_vec = np.array(embed([query])[0], dtype=np.float64)

        # 余弦相似度 = (A·B) / (||A|| * ||B||)
        # 对整个矩阵批量计算，避免逐条循环
        doc_norms = np.linalg.norm(self.matrix, axis=1)        # (n,)
        q_norm = np.linalg.norm(q_vec)                          # 标量
        denom = doc_norms * q_norm
        # 防止除零
        denom[denom == 0] = 1e-10
        sims = (self.matrix @ q_vec) / denom                   # (n,)

        k = min(top_k, len(self.chunks))
        # 取相似度最大的 k 个下标（降序）
        top_idx = np.argsort(sims)[::-1][:k]
        return [(self.chunks[i], float(sims[i])) for i in top_idx]


# ============================================================
# 6. 拼接 Prompt
# ============================================================
PROMPT_TEMPLATE = """你是一个严谨的客服助手，请只根据下面提供的【参考资料】回答用户问题。
如果参考资料中没有相关信息，请直接回答"根据已知资料无法回答"，不要编造。

【参考资料】
{context}

【用户问题】
{question}

【你的回答】
"""


def build_prompt(question: str, retrieved: Sequence[Tuple[str, float]]) -> str:
    """把检索到的文本块作为上下文拼接到 Prompt 中。"""
    context = "\n\n".join(
        f"[{i + 1}] {chunk}" for i, (chunk, _score) in enumerate(retrieved)
    )
    return PROMPT_TEMPLATE.format(context=context, question=question)


# ============================================================
# 7. LLM 生成
# ============================================================
def generate(prompt: str) -> str:
    """调用 LLM（OpenAI 兼容接口）生成回答。"""
    from openai import OpenAI

    client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_API_BASE)
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )
    return resp.choices[0].message.content.strip()


# ============================================================
# 端到端演示
# ============================================================
SAMPLE_DOC = """AI智能客服系统的退货政策

用户在购买商品后7天内可以申请无理由退货。退货商品需保持完好，不影响二次销售。
食品类、贴身衣物等特殊商品一经售出，非质量问题不支持退货。

退款将在收到退货商品并验收合格后的1-3个工作日内原路退回。
如果使用优惠券下单，退货后优惠券不予返还，仅退还实际支付金额。

物流配送时间为工作日48小时内发货，偏远地区可能延长至72小时。
用户可通过订单详情页实时查看物流状态，也可联系在线客服查询。

发票可在订单完成后自助申请电子发票，发票内容为商品明细。
如需开具增值税专用发票，请联系客服并提供企业开票信息。
"""


def run_demo() -> None:
    print("=" * 60)
    print("RAG 生命周期演示（纯 Python + numpy + openai）")
    print("=" * 60)

    # 1. 文档加载
    print("\n[1] 加载文档")
    text = SAMPLE_DOC  # 实际可用 load_document("knowledge.txt")
    print(f"    文档长度: {len(text)} 字符")

    # 2. 切片
    print("\n[2] 文本切片（按段落，max_chars=80）")
    chunks = chunk_by_paragraph(text, max_chars=80)
    for i, c in enumerate(chunks):
        print(f"    #{i + 1} ({len(c)}字): {c[:40]}...")

    # 3 + 4. 向量化 + 存储
    print(f"\n[3] 向量化（后端: {EMBED_BACKEND}）并构建索引")
    store = VectorStore()
    store.add(chunks)
    print(f"    索引矩阵形状: {store.matrix.shape}")

    # 5. 检索
    question = "多长时间退钱？"
    # question = "物流配送时间为24小时内，对吗"
    print(f"\n[4] 检索 Top-3（问题: {question}）")
    retrieved = store.retrieve(question, top_k=3)
    for chunk, score in retrieved:
        print(f"    [相似度 {score:.4f}] {chunk[:40]}...")

    # 6. 拼接 Prompt
    print("\n[5] 拼接 Prompt")
    prompt = build_prompt(question, retrieved)
    print(prompt)

    # 7. LLM 生成
    print("[6] 调用 LLM 生成回答")
    try:
        answer = generate(prompt)
        print(answer)
    except Exception as e:
        print(f"    [LLM 调用失败，跳过生成] {e}")
        print("    提示：请检查 LLM_API_KEY / LLM_API_BASE 是否可用。")


if __name__ == "__main__":
    run_demo()

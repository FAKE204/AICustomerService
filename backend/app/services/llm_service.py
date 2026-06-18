import logging
from typing import Dict, List, Optional

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.api_base = settings.LLM_API_BASE.rstrip("/")
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE

    async def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.api_key:
            return self._fallback_response(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
                logger.info("llm response json: %s", body)
                return body["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.error("LLM 调用失败: %s", exc)
            return self._fallback_response(messages)

    def _fallback_response(self, messages: List[Dict[str, str]]) -> str:
        latest_message = next(
            (message["content"] for message in reversed(messages) if message.get("role") == "user"),
            "",
        )
        if not latest_message:
            return "您好，请告诉我您想咨询商品、订单还是售后问题。"

        return (
            "当前未配置外部大模型服务，我已收到您的问题："
            f"{latest_message}。您可以继续提供订单号、商品名称或售后诉求，我会按规则继续协助。"
        )

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

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
        thinking: Optional[str] = "disabled",
    ) -> str:
        if not self.api_key:
            return self._fallback_response(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking=thinking,
            stream=False,
        )

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
                return self._extract_message_content(body).strip()
        except Exception as exc:
            logger.error("LLM 调用失败: %s", exc)
            return self._fallback_response(messages)

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking: Optional[str] = "disabled",
    ) -> AsyncIterator[str]:
        if not self.api_key:
            yield self._fallback_response(messages)
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking=thinking,
            stream=True,
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for chunk in self._iter_stream_content(response):
                        if chunk:
                            yield chunk
        except Exception as exc:
            logger.error("LLM 流式调用失败: %s", exc)
            yield self._fallback_response(messages)

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        thinking: Optional[str],
        stream: bool,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "stream": stream,
        }
        if thinking:
            payload["thinking"] = {"type": thinking}
        return payload

    async def _iter_stream_content(self, response: httpx.Response) -> AsyncIterator[str]:
        data_lines: list[str] = []
        async for line in response.aiter_lines():
            if line == "":
                should_stop, content = self._consume_stream_event(data_lines)
                data_lines.clear()
                if content:
                    yield content
                if should_stop:
                    return
                continue

            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())

        if data_lines:
            _, content = self._consume_stream_event(data_lines)
            if content:
                yield content

    def _consume_stream_event(self, data_lines: list[str]) -> tuple[bool, str]:
        if not data_lines:
            return False, ""

        data = "\n".join(data_lines).strip()
        if not data:
            return False, ""
        if data == "[DONE]":
            return True, ""

        body = json.loads(data)
        return False, self._extract_delta_content(body)

    def _extract_message_content(self, body: Dict[str, Any]) -> str:
        choices = body.get("choices") or []
        if not choices:
            return ""

        message = choices[0].get("message") or {}
        return self._normalize_content(message.get("content"))

    def _extract_delta_content(self, body: Dict[str, Any]) -> str:
        choices = body.get("choices") or []
        if not choices:
            return ""

        delta = choices[0].get("delta") or {}
        return self._normalize_content(delta.get("content"))

    def _normalize_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts)
        return ""

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

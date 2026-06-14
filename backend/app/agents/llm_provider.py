"""Abstraction du provider LLM — Claude (principal) + Mistral + Gemini (fallbacks).

Ordre de priorité :
  1. Claude (Anthropic) — via l'API Anthropic, aucune clé requise pour le POC
  2. Mistral — dès que la clé sera disponible
  3. Gemini — dernier recours

Centralise les appels LLM avec :
  - Fallback automatique entre providers
  - Streaming (Server-Sent Events) pour le chatbot
  - Logging structuré
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# URL de l'API Anthropic — le proxy interne ne nécessite pas de clé API
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class LLMRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    role: LLMRole
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


def _build_anthropic_payload(
    messages: list[LLMMessage],
    model: str,
    max_tokens: int,
    temperature: float,
    stream: bool = False,
) -> dict[str, Any]:
    """Construit le payload pour l'API Anthropic.

    L'API Anthropic sépare le message system du reste :
    messages = [user/assistant, ...], system = "..."
    """
    system_parts = [m.content for m in messages if m.role == LLMRole.SYSTEM]
    user_msgs = [
        {"role": m.role.value, "content": m.content}
        for m in messages
        if m.role != LLMRole.SYSTEM
    ]
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": user_msgs,
        "stream": stream,
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    return payload


def _anthropic_headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": ANTHROPIC_VERSION,
    }
    if settings.anthropic_api_key:
        headers["x-api-key"] = settings.anthropic_api_key
    return headers


class LLMProvider:
    """Provider LLM avec fallback automatique : Claude → Mistral → Gemini.

    Usage:
        provider = LLMProvider()
        response = await provider.complete([
            LLMMessage(LLMRole.SYSTEM, "Tu es un expert CVC..."),
            LLMMessage(LLMRole.USER, "Alarme X déclenchée, que faire ?"),
        ])
        print(response.content)
    """

    def __init__(self) -> None:
        self._mistral_client: Any = None
        self._gemini_client: Any = None
        self._groq_client: Any = None

    # ------------------------------------------------------------------
    # Completion non-streaming
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        use_small_model: bool = False,  # ignoré pour Claude, conservé pour compat
    ) -> LLMResponse:
        """Complétion non-streaming, avec fallback Claude → Mistral → Gemini."""
        chosen_model = model or settings.anthropic_model
        temp = temperature if temperature is not None else settings.llm_temperature
        tok = max_tokens or settings.anthropic_max_tokens
        start = time.perf_counter()

        # 1. Tentative Claude
        try:
            return await self._claude_complete(messages, chosen_model, temp, tok, start)
        except Exception as e:  # noqa: BLE001
            logger.warning("llm.claude.failed", error=str(e), fallback="mistral")

        # 2. Fallback Mistral (si clé disponible)
        if settings.mistral_api_key:
            try:
                return await self._mistral_complete(messages, start)
            except Exception as e:  # noqa: BLE001
                logger.warning("llm.mistral.failed", error=str(e), fallback="groq")

        # 3. Fallback Groq (si clé disponible)
        if settings.groq_api_key:
            try:
                return await self._groq_complete(messages, start)
            except Exception as e:  # noqa: BLE001
                logger.warning("llm.groq.failed", error=str(e), fallback="gemini")

        # 4. Fallback Gemini (si clé disponible)
        if settings.gemini_api_key:
            return await self._gemini_fallback(messages, start)

        raise RuntimeError(
            "Aucun provider LLM disponible. "
            "Vérifier ANTHROPIC_API_KEY, MISTRAL_API_KEY ou GROQ_API_KEY dans .env"
        )

    async def _claude_complete(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        start: float,
    ) -> LLMResponse:
        payload = _build_anthropic_payload(messages, model, max_tokens, temperature)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers=_anthropic_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["content"][0]["text"] if data.get("content") else ""
        usage = data.get("usage", {})
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "llm.claude.ok",
            model=model,
            latency_ms=latency_ms,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )
        return LLMResponse(
            content=content,
            model=model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=latency_ms,
        )

    async def _mistral_complete(
        self, messages: list[LLMMessage], start: float
    ) -> LLMResponse:
        from mistralai import Mistral

        if self._mistral_client is None:
            self._mistral_client = Mistral(api_key=settings.mistral_api_key)
        response = await self._mistral_client.chat.complete_async(
            model=settings.mistral_model,
            messages=[{"role": m.role.value, "content": m.content} for m in messages],
            temperature=settings.llm_temperature,
            max_tokens=settings.mistral_max_tokens,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=settings.mistral_model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            latency_ms=latency_ms,
        )

    async def _groq_complete(
        self, messages: list[LLMMessage], start: float
    ) -> LLMResponse:
        from openai import AsyncOpenAI

        if self._groq_client is None:
            self._groq_client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        response = await self._groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": m.role.value, "content": m.content} for m in messages],
            temperature=settings.llm_temperature,
            max_tokens=2000,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("llm.groq.ok", model=settings.groq_model, latency_ms=latency_ms)
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=settings.groq_model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            latency_ms=latency_ms,
        )

    async def _gemini_fallback(
        self, messages: list[LLMMessage], start_time: float
    ) -> LLMResponse:
        import google.generativeai as genai

        if self._gemini_client is None:
            genai.configure(api_key=settings.gemini_api_key)
            self._gemini_client = genai.GenerativeModel(settings.gemini_model)
        prompt = "\n\n".join(f"[{m.role.value.upper()}]\n{m.content}" for m in messages)
        response = await self._gemini_client.generate_content_async(prompt)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return LLMResponse(
            content=response.text,
            model=settings.gemini_model,
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # Streaming SSE (pour le chatbot)
    # ------------------------------------------------------------------

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Streaming par chunks (pour SSE dans le chatbot).

        Tente Claude en streaming. Si indisponible et Mistral dispo → fallback.
        """
        chosen_model = model or settings.anthropic_model
        temp = temperature if temperature is not None else settings.llm_temperature
        max_tok = settings.anthropic_max_tokens

        try:
            async for chunk in self._claude_stream(messages, chosen_model, temp, max_tok):
                yield chunk
            return
        except Exception as e:  # noqa: BLE001
            logger.warning("llm.claude.stream.failed", error=str(e))

        if settings.mistral_api_key:
            try:
                async for chunk in self._mistral_stream(messages):
                    yield chunk
                return
            except Exception as e:  # noqa: BLE001
                logger.warning("llm.mistral.stream.failed", error=str(e))

        if settings.groq_api_key:
            try:
                async for chunk in self._groq_stream(messages):
                    yield chunk
                return
            except Exception as e:  # noqa: BLE001
                logger.warning("llm.groq.stream.failed", error=str(e))

        if settings.gemini_api_key:
            try:
                async for chunk in self._gemini_stream(messages):
                    yield chunk
                return
            except Exception as e:  # noqa: BLE001
                logger.warning("llm.gemini.stream.failed", error=str(e))

        raise RuntimeError(
            "Aucun provider LLM disponible. "
            "Vérifier ANTHROPIC_API_KEY, MISTRAL_API_KEY ou GROQ_API_KEY dans .env"
        )

    async def _claude_stream(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        payload = _build_anthropic_payload(
            messages, model, max_tokens, temperature, stream=True
        )
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                ANTHROPIC_API_URL,
                headers=_anthropic_headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield text

    async def _mistral_stream(
        self, messages: list[LLMMessage]
    ) -> AsyncIterator[str]:
        from mistralai import Mistral

        if self._mistral_client is None:
            self._mistral_client = Mistral(api_key=settings.mistral_api_key)
        stream = await self._mistral_client.chat.stream_async(
            model=settings.mistral_model,
            messages=[{"role": m.role.value, "content": m.content} for m in messages],
            temperature=settings.llm_temperature,
        )
        async for chunk in stream:
            delta = chunk.data.choices[0].delta.content
            if delta:
                yield delta

    async def _groq_stream(
        self, messages: list[LLMMessage]
    ) -> AsyncIterator[str]:
        from openai import AsyncOpenAI

        if self._groq_client is None:
            self._groq_client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        stream = await self._groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": m.role.value, "content": m.content} for m in messages],
            temperature=settings.llm_temperature,
            max_tokens=2000,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def _gemini_stream(
        self, messages: list[LLMMessage]
    ) -> AsyncIterator[str]:
        import google.generativeai as genai

        if self._gemini_client is None:
            genai.configure(api_key=settings.gemini_api_key)
            self._gemini_client = genai.GenerativeModel(settings.gemini_model)
        prompt = "\n\n".join(f"[{m.role.value.upper()}]\n{m.content}" for m in messages)
        response = await self._gemini_client.generate_content_async(prompt, stream=True)
        async for chunk in response:
            text = chunk.text if hasattr(chunk, "text") else ""
            if text:
                yield text

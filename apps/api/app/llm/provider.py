"""Gemini REST adapter; credentials, model and limits come exclusively from settings."""

import asyncio
import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.llm.prompts import SYSTEM_PROMPT
from app.schemas.investigation import AgentResult


class ProviderError(Exception):
    pass


class LLMProvider(Protocol):
    mode: str

    async def propose(self, role: str, evidence: dict[str, Any]) -> AgentResult: ...


class GeminiProvider:
    mode = "gemini"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def propose(self, role: str, evidence: dict[str, Any]) -> AgentResult:
        config = self.settings
        if not config.llm_api_key or not config.llm_model:
            raise ProviderError("MODEL_CONFIGURATION_MISSING")
        context = json.dumps({"role": role, "evidence": evidence}, ensure_ascii=False)
        if len(context) > config.investigation_max_context_chars:
            raise ProviderError("MODEL_CONTEXT_BUDGET_EXCEEDED")
        request_body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": context}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": AgentResult.model_json_schema(),
                    "maxOutputTokens": config.llm_max_output_tokens,
                },
            }
        ).encode()

        def send() -> str:
            request = Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{config.llm_model}:generateContent",
                data=request_body,
                headers={"Content-Type": "application/json", "x-goog-api-key": config.llm_api_key},
            )
            with urlopen(request, timeout=config.llm_timeout_seconds) as response:
                payload = json.loads(response.read(1000000))
            return str(payload["candidates"][0]["content"]["parts"][0]["text"])

        for attempt in range(config.llm_max_retries + 1):
            try:
                async with asyncio.timeout(config.llm_timeout_seconds + 1):
                    raw = await asyncio.to_thread(send)
                return AgentResult.model_validate_json(raw)
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == config.llm_max_retries:
                    raise ProviderError(f"MODEL_HTTP_{exc.code}") from None
            except (URLError, TimeoutError):
                if attempt == config.llm_max_retries:
                    raise ProviderError("MODEL_UNAVAILABLE") from None
            except (ValueError, KeyError, IndexError, TypeError):
                raise ProviderError("MODEL_INVALID_OUTPUT") from None
            await asyncio.sleep(0.5 * (2**attempt))
        raise ProviderError("MODEL_RETRIES_EXHAUSTED")

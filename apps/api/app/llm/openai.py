"""Bounded official Responses API adapter; never return provider error bodies."""

import asyncio
import json
from typing import Any, TypeVar

from openai import APIError, APIStatusError, AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.llm.prompts import SYSTEM_PROMPT
from app.llm.proposals import Proposals
from app.llm.provider import ProviderError
from app.schemas.investigation import AgentResult

Output = TypeVar("Output", bound=BaseModel)


class OpenAIProvider:
    mode = "openai"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(
        self, task: str, evidence: dict[str, Any], schema: type[Output], instructions: str
    ) -> Output:
        config = self.settings
        key = config.openai_api_key or config.llm_api_key
        if not key:
            raise ProviderError("MODEL_CONFIGURATION_MISSING")
        context = json.dumps({"task": task, "evidence": evidence}, ensure_ascii=False)
        if len(context) > config.investigation_max_context_chars:
            raise ProviderError("MODEL_CONTEXT_BUDGET_EXCEEDED")
        try:
            async with (
                AsyncOpenAI(
                    api_key=key,
                    timeout=config.llm_timeout_seconds,
                    max_retries=config.llm_max_retries,
                ) as client,
                asyncio.timeout((config.llm_timeout_seconds + 2) * (config.llm_max_retries + 1)),
            ):
                response = await client.responses.parse(
                    model=config.llm_model or config.openai_model,
                    instructions=instructions,
                    input=context,
                    text_format=schema,
                    max_output_tokens=config.llm_max_output_tokens,
                    store=False,
                )
                if response.status != "completed" or response.output_parsed is None:
                    raise ProviderError("MODEL_INVALID_OUTPUT")
                return schema.model_validate(response.output_parsed)
        except APIStatusError as exc:
            raise ProviderError(f"MODEL_HTTP_{exc.status_code}") from None
        except (APIError, TimeoutError):
            raise ProviderError("MODEL_UNAVAILABLE") from None
        except (ValidationError, ValueError, TypeError):
            raise ProviderError("MODEL_INVALID_OUTPUT") from None

    async def propose(self, role: str, evidence: dict[str, Any]) -> AgentResult:
        result = await self.generate(
            role,
            evidence,
            Proposals,
            SYSTEM_PROMPT
            + "\nOUTPUT SCHEMA: Proposals. Encode each anchor's exact expected field value as "
            "a JSON string in expected_json. Do not alter the source value.",
        )
        try:
            return result.validated()
        except (ValueError, TypeError):
            raise ProviderError("MODEL_INVALID_OUTPUT") from None

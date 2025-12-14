from __future__ import annotations
import json
import os
from dataclasses import dataclass
from typing import Any, Optional, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


class LLMCallError(RuntimeError):
    """Raised when an LLM invocation fails or returns invalid content."""


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Immutable configuration for the LLM client."""

    api_key: str
    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.2
    base_url: str = "https://openrouter.ai/api/v1"

    @classmethod
    def from_env(cls) -> LLMConfig:
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMCallError("OPENROUTER_API_KEY or OPENAI_API_KEY is not set")
        model = os.getenv("OPENROUTER_MODEL") or os.getenv(
            "OPENAI_MODEL", "openai/gpt-4o-mini"
        )
        temperature = float(
            os.getenv("OPENROUTER_TEMPERATURE")
            or os.getenv("OPENAI_TEMPERATURE", "0.2")
        )
        base_url = os.getenv("OPENROUTER_BASE_URL") or os.getenv(
            "OPENAI_BASE_URL", "https://openrouter.ai/api/v1"
        )
        return cls(
            api_key=api_key, model=model, temperature=temperature, base_url=base_url
        )


@dataclass(frozen=True, slots=True)
class LLMClient:
    """Wrapper around the OpenAI Responses API that enforces structured output."""

    config: LLMConfig
    _client: Optional[OpenAI] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_client",
            OpenAI(api_key=self.config.api_key, base_url=self.config.base_url),
        )

    def invoke(self, *, prompt: str, output_model: Type[T]) -> T:
        """Execute the provided prompt and parse it into the expected model."""

        try:
            response = self._client.responses.parse(  # type: ignore[union-attr]
                model=self.config.model,
                input=prompt,
                temperature=self.config.temperature,
                text_format=output_model,
            )
        except Exception as exc:  # pragma: no cover - network errors
            raise LLMCallError("Failed to execute LLM call") from exc

        payload = response.output_parsed
        try:
            return output_model.model_validate(payload)
        except ValidationError as exc:
            raise LLMCallError("LLM response failed schema validation") from exc

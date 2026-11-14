"""LiteLLM-backed implementation of the `LLM` protocol."""

import logging
from typing import Any

from app.core.exceptions import LLMInvocationError

logger = logging.getLogger(__name__)


class LiteLLMClient:
    """Calls any LiteLLM-supported model (e.g. `anthropic/claude-...`, `ollama/llama3`)."""

    def __init__(
        self,
        model: str,
        api_key: str | None,
        api_base: str | None,
        temperature: float,
        timeout_seconds: int,
    ) -> None:
        self._kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "timeout": timeout_seconds,
        }
        # Optional: when unset, LiteLLM falls back to the provider's own env vars.
        if api_key:
            self._kwargs["api_key"] = api_key
        if api_base:
            self._kwargs["api_base"] = api_base

    def complete(self, system: str, user: str) -> str:
        import litellm  # imported lazily: it is slow to import and only needed for this provider

        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            response = litellm.completion(messages=messages, **self._kwargs)
        except Exception as exc:
            logger.exception("LiteLLM call failed")
            raise LLMInvocationError(f"LLM request failed: {exc}") from exc
        return response.choices[0].message.content or ""

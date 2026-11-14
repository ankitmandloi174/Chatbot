"""Provider-agnostic LLM client built on LangChain chat models."""

import json
import logging
import re
from typing import Any, Protocol

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import Settings
from app.core.exceptions import LLMConfigError, LLMInvocationError

logger = logging.getLogger(__name__)


class LLM(Protocol):
    """Interface the analysis layer depends on (easy to fake in tests)."""

    def complete(self, system: str, user: str) -> str: ...


def build_chat_model(settings: Settings) -> BaseChatModel:
    """Create the LangChain chat model for the configured provider."""
    provider = settings.llm_provider
    common: dict[str, Any] = {"temperature": settings.llm_temperature}

    if provider == "openai":
        _require(settings.openai_api_key, "OPENAI_API_KEY", provider)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            timeout=settings.llm_timeout_seconds,
            **common,
        )
    if provider == "openrouter":
        _require(settings.openrouter_api_key, "OPENROUTER_API_KEY", provider)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=settings.llm_timeout_seconds,
            **common,
        )
    if provider == "gemini":
        _require(settings.gemini_api_key, "GEMINI_API_KEY", provider)
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            timeout=settings.llm_timeout_seconds,
            **common,
        )
    raise LLMConfigError(f"Unsupported LLM provider '{provider}'")


def build_llm(settings: Settings) -> LLM:
    """Create the `LLM` for the configured provider."""
    if settings.llm_provider == "litellm":
        _require(settings.litellm_model, "LITELLM_MODEL", "litellm")
        from app.services.llm.litellm_client import LiteLLMClient

        return LiteLLMClient(
            model=settings.litellm_model,  # type: ignore[arg-type]  # checked by _require
            api_key=settings.litellm_api_key,
            api_base=settings.litellm_api_base,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return LangChainLLM(build_chat_model(settings))


def _require(value: str | None, env_name: str, provider: str) -> None:
    if not value:
        raise LLMConfigError(f"LLM provider '{provider}' selected but {env_name} is not set in .env")


def _content_to_text(content: Any) -> str:
    """Normalise LangChain content (str or list of blocks) to plain text."""
    if isinstance(content, str):
        return content
    parts = [b if isinstance(b, str) else b.get("text", "") for b in content]
    return "".join(parts)


class LangChainLLM:
    """Thin wrapper turning a LangChain chat model into the `LLM` protocol."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    def complete(self, system: str, user: str) -> str:
        try:
            response = self._model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        except Exception as exc:
            logger.exception("LLM call failed")
            raise LLMInvocationError(f"LLM request failed: {exc}") from exc
        return _content_to_text(response.content)


_FENCE = re.compile(r"```(?:\w+)?\s*\n?(.*?)```", re.DOTALL)


def extract_fenced(text: str, default_to_text: bool = True) -> str:
    """Return the first fenced block's body, or the raw text if none."""
    match = _FENCE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip() if default_to_text else ""


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from an LLM reply, tolerating fences and prose."""
    candidate = extract_fenced(text)
    start, end = candidate.find("{"), candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in LLM output")
    return json.loads(candidate[start : end + 1])

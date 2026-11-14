from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.exceptions import LLMConfigError, LLMInvocationError
from app.services.llm.client import build_llm
from app.services.llm.litellm_client import LiteLLMClient


def _settings(tmp_path, **overrides) -> Settings:
    return Settings(data_dir=tmp_path, llm_provider="litellm", _env_file=None, **overrides)


def test_litellm_requires_model(tmp_path):
    with pytest.raises(LLMConfigError, match="LITELLM_MODEL"):
        build_llm(_settings(tmp_path))


def test_litellm_selected_from_settings(tmp_path):
    llm = build_llm(_settings(tmp_path, litellm_model="ollama/llama3", litellm_api_base="http://x:11434"))
    assert isinstance(llm, LiteLLMClient)
    assert llm._kwargs["model"] == "ollama/llama3"
    assert llm._kwargs["api_base"] == "http://x:11434"
    assert "api_key" not in llm._kwargs  # optional, omitted when unset


def test_litellm_complete_sends_system_and_user(monkeypatch):
    import litellm

    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))])

    monkeypatch.setattr(litellm, "completion", fake_completion)
    client = LiteLLMClient("m", "key", None, temperature=0.0, timeout_seconds=5)
    assert client.complete("sys", "usr") == "hi"
    assert captured["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]
    assert captured["api_key"] == "key"


def test_litellm_errors_are_wrapped(monkeypatch):
    import litellm

    def boom(**_):
        raise RuntimeError("down")

    monkeypatch.setattr(litellm, "completion", boom)
    with pytest.raises(LLMInvocationError, match="down"):
        LiteLLMClient("m", None, None, 0.0, 5).complete("s", "u")

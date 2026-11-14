"""Centralised application configuration, loaded from environment / .env."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["openai", "gemini", "openrouter", "litellm"]


class Settings(BaseSettings):
    """All tunable values. Override via environment variables or a `.env` file."""

    # `../.env` lets the backend pick up the repo-root file when run locally.
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), extra="ignore", case_sensitive=False
    )

    # --- LLM -------------------------------------------------------------
    llm_provider: LLMProvider = "openai"
    llm_temperature: float = 0.0
    llm_timeout_seconds: int = 90

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # LiteLLM model string, e.g. "anthropic/claude-sonnet-4-5" or "ollama/llama3".
    litellm_model: str | None = None
    litellm_api_key: str | None = None
    litellm_api_base: str | None = None

    # --- Storage ---------------------------------------------------------
    data_dir: Path = Path("./data")

    # --- Uploads ---------------------------------------------------------
    max_upload_mb: int = Field(default=200, gt=0)
    max_files_per_upload: int = Field(default=10, gt=0)
    max_upload_workers: int = Field(default=4, gt=0)

    # --- Cleaning --------------------------------------------------------
    max_null_ratio_to_keep_column: float = 0.9
    median_fill_max_null_ratio: float = 0.05

    # --- Retrieval -------------------------------------------------------
    retrieval_top_k: int = 12
    relationship_min_overlap: float = 0.5

    # --- Analysis --------------------------------------------------------
    max_code_retries: int = Field(default=3, ge=0, le=5)
    sandbox_timeout_seconds: int = 60
    sandbox_memory_mb: int = 4096
    result_max_rows: int = 1000
    history_turns: int = 6

    # --- Follow-up suggestions -------------------------------------------
    follow_up_count: int = Field(default=3, ge=1, le=5)
    follow_up_llm_enabled: bool = True  # extra LLM call for result-specific questions

    # --- API -------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'app.db').resolve()}"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def parquet_dir(self) -> Path:
        return self.data_dir / "parquet"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        """Create every storage directory the app writes to."""
        for path in (self.data_dir, self.raw_dir, self.parquet_dir, self.chroma_dir):
            path.mkdir(parents=True, exist_ok=True)

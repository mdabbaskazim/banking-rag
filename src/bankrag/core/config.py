"""Configuration management for Banking RAG.

All configuration is loaded via environment variables and validated through
the Settings class in accordance with ARCHITECTURE.md Section 11.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bankrag.core.errors import ConfigurationError

AppEnv = Literal["local", "test", "cloud"]


class Settings(BaseSettings):
    """Central configuration class for Banking RAG."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Environment & Logging
    app_env: AppEnv = Field(default="local", description="Environment: local, test, cloud")
    log_level: str = Field(default="INFO", description="Standard logging level")

    # Neon Postgres Connection Strings
    database_url: str = Field(
        default="",
        description="Neon direct connection string for migrations, checkpointer, and workers",
    )
    database_pooled_url: str = Field(
        default="",
        description="Neon pooled connection string for request queries",
    )

    # Qdrant Vector Store
    qdrant_url: str = Field(default="", description="Qdrant cluster URL")
    qdrant_api_key: str = Field(default="", description="Qdrant API key")
    qdrant_collection_alias: str = Field(
        default="chunks", description="Collection alias used by the application"
    )

    # LLM Settings (Google AI Studio / Gemini API)
    gemini_api_key: str = Field(default="", description="Google AI Studio Gemini API key")
    llm_model: str = Field(default="gemini-2.5-flash", description="Configured Gemini model ID")
    llm_rpm: int = Field(default=30, ge=1, description="LLM requests per minute limit")
    llm_tpm: int = Field(default=16000, ge=1, description="LLM tokens per minute limit")
    llm_rpd: int = Field(default=14400, ge=1, description="LLM requests per day limit")
    llm_timeout_s: int = Field(default=60, ge=1, description="LLM request timeout in seconds")
    llm_max_query_tokens: int = Field(
        default=8000, ge=1, description="Max token budget per query run"
    )
    fake_llm: bool = Field(default=False, description="Use fake LLM provider")

    # Local Model Settings
    embed_model: str = Field(default="BAAI/bge-m3", description="Embedding model identifier")
    hf_home: str = Field(default="./.cache/hf", description="Hugging Face cache directory")

    # Retrieval & Gate Thresholds
    prefetch_limit: int = Field(default=30, ge=1, description="Prefetch limit for hybrid search")
    retrieve_k: int = Field(default=10, ge=1, description="Top K documents retrieved after fusion")
    llm_context_k: int = Field(default=5, ge=1, description="Top K documents passed to LLM")
    gate_strong: float = Field(default=0.75, ge=0.0, le=1.0, description="Strong evidence score")
    gate_weak: float = Field(default=0.45, ge=0.0, le=1.0, description="Weak evidence score")
    hhem_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="Entailment threshold")
    max_verify_retries: int = Field(
        default=2, ge=0, description="Max re-asks after verification failure"
    )
    risky_topics: str = Field(
        default="dispute,fraud liability,eligibility",
        description="Comma-separated topics that trigger mandatory human escalation",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"Invalid log_level: {v}. Must be one of {valid_levels}")
        return upper

    @property
    def risky_topics_list(self) -> list[str]:
        """Parsed list of risky topics."""
        return [t.strip().lower() for t in self.risky_topics.split(",") if t.strip()]

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def is_cloud(self) -> bool:
        return self.app_env == "cloud"

    def validate_cloud_requirements(self) -> None:
        """Validate that all credentials required for cloud deployment are present."""
        missing: list[str] = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.qdrant_url:
            missing.append("QDRANT_URL")
        if not self.qdrant_api_key:
            missing.append("QDRANT_API_KEY")
        if not self.gemini_api_key and not self.fake_llm:
            missing.append("GEMINI_API_KEY")

        if missing:
            raise ConfigurationError(
                f"Missing required cloud environment variables: {', '.join(missing)}"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton instance."""
    return Settings()

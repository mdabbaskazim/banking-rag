"""Unit tests for configuration management (Settings)."""

import pytest
from pydantic import ValidationError

from bankrag.core.config import Settings
from bankrag.core.errors import ConfigurationError


def test_default_settings() -> None:
    """Verify that default settings match ARCHITECTURE.md specifications."""
    settings = Settings(
        app_env="local",
        database_url="",
        qdrant_url="",
        gemini_api_key="",
    )
    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.qdrant_collection_alias == "chunks"
    assert settings.llm_rpm == 30
    assert settings.llm_tpm == 16000
    assert settings.llm_rpd == 14400
    assert settings.llm_timeout_s == 60
    assert settings.llm_max_query_tokens == 8000
    assert settings.embed_model == "BAAI/bge-m3"
    assert settings.hf_home == "./.cache/hf"
    assert settings.prefetch_limit == 30
    assert settings.retrieve_k == 10
    assert settings.llm_context_k == 5
    assert settings.gate_strong == 0.75
    assert settings.gate_weak == 0.45
    assert settings.hhem_threshold == 0.75
    assert settings.max_verify_retries == 2
    assert "dispute" in settings.risky_topics_list
    assert "fraud liability" in settings.risky_topics_list
    assert "eligibility" in settings.risky_topics_list
    assert settings.is_local is True
    assert settings.is_test is False
    assert settings.is_cloud is False


def test_invalid_log_level() -> None:
    """Ensure invalid log level raises ValidationError."""
    with pytest.raises(ValidationError):
        Settings(log_level="NOT_A_LEVEL")


def test_risky_topics_parsing() -> None:
    """Ensure comma-separated risky topics are cleanly split and trimmed."""
    settings = Settings(risky_topics=" Dispute , Fraud Liability , Eligibility , Arbitration ")
    assert settings.risky_topics_list == [
        "dispute",
        "fraud liability",
        "eligibility",
        "arbitration",
    ]


def test_cloud_requirements_validation_failure() -> None:
    """Verify validate_cloud_requirements raises ConfigurationError when keys are missing."""
    settings = Settings(
        app_env="cloud",
        database_url="",
        qdrant_url="",
        qdrant_api_key="",
        gemini_api_key="",
        fake_llm=False,
    )
    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_cloud_requirements()
    assert "DATABASE_URL" in str(exc_info.value)
    assert "QDRANT_URL" in str(exc_info.value)
    assert "QDRANT_API_KEY" in str(exc_info.value)
    assert "GEMINI_API_KEY" in str(exc_info.value)


def test_cloud_requirements_validation_success() -> None:
    """Verify validate_cloud_requirements succeeds when all cloud keys are provided."""
    settings = Settings(
        app_env="cloud",
        database_url="postgresql+psycopg://user:pass@ep-host.neon.tech/bankrag",
        qdrant_url="https://qdrant.example.com",
        qdrant_api_key="secret-key",
        gemini_api_key="gemini-key",
    )
    # Should not raise
    settings.validate_cloud_requirements()

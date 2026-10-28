"""Unit tests for structured logging and security masking."""

from unittest.mock import MagicMock

from bankrag.core.logging import (
    configure_logging,
    get_logger,
    redact_dict_secrets,
    redact_secrets,
    sanitize_question,
)


def test_redact_secrets_top_level() -> None:
    event_dict = {
        "event": "client_initialized",
        "api_key": "super_secret_123",
        "gemini_api_key": "ai_studio_secret",
        "user_token": "bearer_xyz",
        "password": "db_password",
        "safe_field": "hello world",
    }
    mock_logger = MagicMock()
    result = redact_secrets(mock_logger, "info", event_dict)

    assert result["api_key"] == "[REDACTED]"
    assert result["gemini_api_key"] == "[REDACTED]"
    assert result["user_token"] == "[REDACTED]"
    assert result["password"] == "[REDACTED]"
    assert result["safe_field"] == "hello world"


def test_redact_secrets_nested() -> None:
    nested = {
        "config": {
            "qdrant_api_key": "qdrant_sec",
            "normal_value": 42,
        }
    }
    redacted = redact_dict_secrets(nested)
    assert redacted["config"]["qdrant_api_key"] == "[REDACTED]"
    assert redacted["config"]["normal_value"] == 42


def test_sanitize_question_at_info() -> None:
    raw_question = "What is the penalty for early withdrawal of a fixed deposit?"
    event_dict = {"event": "query_received", "question": raw_question}
    mock_logger = MagicMock()

    result = sanitize_question(mock_logger, "info", event_dict)
    assert "question" not in result
    assert result["question_len"] == len(raw_question)
    assert "question_hash" in result
    assert len(result["question_hash"]) == 12


def test_configure_and_get_logger() -> None:
    configure_logging("DEBUG")
    logger = get_logger("test_module")
    assert logger is not None

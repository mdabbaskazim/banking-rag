"""Structured JSON logging configuration using structlog.

Complies with ARCHITECTURE.md Section 12:
- Logs go to stdout as structured JSON.
- Secrets are automatically redacted from event dictionaries.
- Sensitive user questions are masked to hash + length at INFO level.
"""

import hashlib
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

SENSITIVE_KEY_SUBSTRINGS = (
    "api_key",
    "token",
    "password",
    "secret",
    "credential",
    "authorization",
)


def redact_secrets(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """Recursively mask values whose keys indicate sensitive information."""
    for key, value in list(event_dict.items()):
        lower_key = str(key).lower()
        if any(substr in lower_key for substr in SENSITIVE_KEY_SUBSTRINGS):
            event_dict[key] = "[REDACTED]"
        elif isinstance(value, dict):
            event_dict[key] = redact_dict_secrets(value)
    return event_dict


def redact_dict_secrets(d: dict[str, Any]) -> dict[str, Any]:
    """Helper to redact sensitive values in nested dictionaries."""
    sanitized: dict[str, Any] = {}
    for k, v in d.items():
        if any(substr in str(k).lower() for substr in SENSITIVE_KEY_SUBSTRINGS):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = redact_dict_secrets(v)
        else:
            sanitized[k] = v
    return sanitized


def sanitize_question(_logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Mask raw question text at INFO and below to hash + length (Rule 10)."""
    if "question" in event_dict and method_name.lower() in ("info", "warning", "error"):
        raw_q = str(event_dict["question"])
        event_dict["question_len"] = len(raw_q)
        event_dict["question_hash"] = hashlib.sha256(raw_q.encode("utf-8")).hexdigest()[:12]
        del event_dict["question"]
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure standard library logging and structlog to output JSON to stdout."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
        force=True,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        redact_secrets,
        sanitize_question,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
        handler.setLevel(numeric_level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structured logger instance bound to the given module name."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]

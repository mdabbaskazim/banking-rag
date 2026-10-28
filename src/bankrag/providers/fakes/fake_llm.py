"""Fake LLM provider for zero-credential unit testing."""

from typing import Any, TypeVar

from pydantic import BaseModel

from bankrag.core.errors import ProviderError
from bankrag.providers.interfaces import LLMProvider

T = TypeVar("T", bound=BaseModel)


class FakeLLMProvider(LLMProvider):
    """In-memory fake LLM provider for unit tests and local mock runs."""

    def __init__(
        self,
        canned_text: str = "Fake LLM text response",
        canned_structured: Any | None = None,
        should_fail: bool = False,
    ) -> None:
        self.canned_text = canned_text
        self.canned_structured = canned_structured
        self.should_fail = should_fail
        self.call_history: list[dict[str, Any]] = []

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        self.call_history.append({"prompt": prompt, "kwargs": kwargs, "type": "text"})
        if self.should_fail:
            raise ProviderError("Fake LLM simulated failure")
        return self.canned_text

    async def generate_structured(self, prompt: str, response_model: type[T], **kwargs: Any) -> T:
        self.call_history.append(
            {
                "prompt": prompt,
                "model": response_model.__name__,
                "kwargs": kwargs,
                "type": "structured",
            }
        )
        if self.should_fail:
            raise ProviderError("Fake LLM simulated structured failure")

        if self.canned_structured is not None:
            if isinstance(self.canned_structured, response_model):
                return self.canned_structured
            if isinstance(self.canned_structured, dict):
                return response_model.model_validate(self.canned_structured)

        # Fallback dummy instance if no canned structured output is given
        try:
            return response_model.model_validate({})
        except Exception:
            # Construct using available field types or construct with dummy data
            dummy_data: dict[str, Any] = {}
            for field_name, field_info in response_model.model_fields.items():
                annotation = field_info.annotation
                if annotation is str:
                    dummy_data[field_name] = "dummy"
                elif annotation is bool:
                    dummy_data[field_name] = False
                elif annotation is int:
                    dummy_data[field_name] = 0
                elif annotation is float:
                    dummy_data[field_name] = 0.0
                elif getattr(annotation, "__origin__", None) is list:
                    dummy_data[field_name] = []
                else:
                    dummy_data[field_name] = None
            return response_model.model_validate(dummy_data)

"""Smoke test for Gemini API and native structured output verification.

Complies with ARCHITECTURE.md Section 14 & 15:
- Uses the official google-genai SDK directly.
- Tests native structured output capability using a Pydantic schema.
- Reports actual success or failure without inventing results.
"""

import argparse
import sys
import time

from pydantic import BaseModel, Field

from bankrag.core.config import get_settings


class BankingSmokeResponse(BaseModel):
    """Schema for validating native structured output."""

    domain: str = Field(description="Domain name, e.g. Retail Banking")
    claim: str = Field(description="A factual statement about banking regulations")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )


def run_smoke_test(model_id: str | None = None) -> int:
    settings = get_settings()
    api_key = settings.gemini_api_key

    if not api_key or api_key in ("placeholder", "your_gemini_api_key_here"):
        print(
            "ERROR: GEMINI_API_KEY is not set or contains a placeholder value.\n"
            "Set a valid Google AI Studio key in .env or environment variable GEMINI_API_KEY.",
            file=sys.stderr,
        )
        return 1

    target_model = model_id or settings.llm_model
    print("[*] Initializing google-genai client...")
    print(f"[*] Target Model ID: {target_model}")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = (
            "Provide a one-sentence factual summary explaining why savings accounts earn interest. "
            "Return the answer in the requested structured schema."
        )

        start_time = time.perf_counter()
        print("[*] Calling Gemini API with structured response schema...")

        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BankingSmokeResponse,
            ),
        )

        duration = time.perf_counter() - start_time

        if not response.text:
            print("[-] ERROR: Received empty response from model.", file=sys.stderr)
            return 1

        print(f"[+] Response received in {duration:.2f}s")
        print("[*] Validating structured output with Pydantic...")

        parsed = BankingSmokeResponse.model_validate_json(response.text)

        print("\n=== SMOKE TEST SUCCEEDED ===")
        print(f"Model: {target_model}")
        print(f"Latency: {duration:.2f}s")
        print(f"Domain: {parsed.domain}")
        print(f"Claim: {parsed.claim}")
        print(f"Confidence: {parsed.confidence}")
        print("============================\n")
        return 0

    except Exception as exc:
        print(f"\n[-] SMOKE TEST FAILED: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for Gemini API structured output.")
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Google Gemini model ID (defaults to LLM_MODEL in settings)",
    )
    args = parser.parse_args()
    sys.exit(run_smoke_test(args.model))


if __name__ == "__main__":
    main()

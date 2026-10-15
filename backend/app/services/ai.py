"""
AI service: Anthropic Claude wrapper.
- Injects brand profile as system context
- Returns strict JSON validated by Pydantic
- Retries once on parse failure
- All prompts live in apps/api/prompts/
"""
import json
import logging
from pathlib import Path
from typing import Any, Type, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.services.claims_guard import ClaimsGuardError, check_claims

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

T = TypeVar("T", bound=BaseModel)

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _build_system_prompt(brand_context: dict | None = None) -> str:
    """Build the system prompt injecting brand profile for tone consistency."""
    base = (
        "You are the AI writing assistant for GlobalReach Growth Engine. "
        "You help create marketing content that is honest, professional, and effective. "
        "You NEVER make unverifiable claims, guarantees, or fake testimonials. "
        "You ALWAYS return valid JSON exactly as requested, no extra text.\n"
    )
    if brand_context:
        base += f"\nBrand context:\n{json.dumps(brand_context, indent=2)}\n"
    return base


def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    path = PROMPTS_DIR / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt template not found: {path}")


async def generate(
    prompt: str,
    response_model: Type[T],
    brand_context: dict | None = None,
    max_tokens: int = 2048,
    model: str = "claude-3-5-sonnet-20241022",
) -> T:
    """
    Generate structured JSON output from Claude, validated against response_model.
    Retries once on parse/validation failure.

    Args:
        prompt: The user-facing prompt.
        response_model: Pydantic model to validate the JSON response against.
        brand_context: Brand profile dict to inject into system context.
        max_tokens: Max output tokens.
        model: Anthropic model ID.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ValueError: If parsing fails after retry.
        ClaimsGuardError: If generated content contains prohibited claims.
    """
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured.")

    client = get_client()
    system = _build_system_prompt(brand_context)

    schema_hint = f"\nRespond ONLY with a JSON object matching this schema:\n{json.dumps(response_model.model_json_schema(), indent=2)}"
    full_prompt = prompt + schema_hint

    for attempt in range(2):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": full_prompt}],
            )
            raw_text = response.content[0].text.strip()

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]

            parsed = json.loads(raw_text)
            result = response_model.model_validate(parsed)

            # Run claims guard on all string fields
            result_json_str = result.model_dump_json()
            check_claims(result_json_str)

            return result

        except (json.JSONDecodeError, ValidationError, ClaimsGuardError) as exc:
            if attempt == 0:
                logger.warning("AI parse attempt 1 failed (%s), retrying...", exc)
                full_prompt = prompt + schema_hint + "\n\nIMPORTANT: Your previous response was not valid JSON. Return ONLY the JSON object, no other text."
                continue
            raise ValueError(f"AI generation failed after retry: {exc}") from exc

    raise ValueError("AI generation failed after 2 attempts.")


async def generate_text(
    prompt: str,
    brand_context: dict | None = None,
    max_tokens: int = 1024,
    model: str = "claude-3-5-sonnet-20241022",
) -> str:
    """
    Generate free-form text (not JSON). Still runs claims guard.
    """
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured.")

    client = get_client()
    system = _build_system_prompt(brand_context)

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    check_claims(text)
    return text

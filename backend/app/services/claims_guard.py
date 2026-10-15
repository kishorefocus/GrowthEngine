"""
Claims guard: rejects AI-generated text containing unverifiable numbers,
fake testimonials, or performance guarantees.

Every AI-generated output passes through this before being stored or shown.
"""
import re
from typing import Optional

# Patterns that must be rejected
_GUARANTEE_PATTERNS = [
    r"\b(guaranteed?|guarantee)\b",
    r"\b(10x|5x|3x|2x)\s+(leads?|revenue|growth|sales|clients?)\b",
    r"\bguaranteed?\s+\d+",
    r"\b100%\s+(success|guaranteed?|effective)\b",
    r"\bmake\s+\$[\d,]+\s+per\s+(day|month|week)\b",
    r"\b(proven|guaranteed?)\s+results?\b",
]

_FAKE_TESTIMONIAL_PATTERNS = [
    r"[-—]\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s*,?\s*(CEO|CTO|CMO|Founder|VP)\b",  # "— John Smith, CEO"
    r"\*(.*?)\*\s*[-—]\s*[A-Z]",  # *quote* — Attribution
]

_UNVERIFIABLE_STAT_PATTERNS = [
    r"\b\d{1,3}%\s+(of\s+(companies|businesses|marketers|founders)|increase|improvement|reduction)\b",
    r"\bover\s+\d+,\d{3}\s+(customers?|users?|companies|businesses)\b",
    r"\bmore\s+than\s+\d+\s+(years?\s+of\s+experience)\b",
]

_ALL_PATTERNS = _GUARANTEE_PATTERNS + _FAKE_TESTIMONIAL_PATTERNS + _UNVERIFIABLE_STAT_PATTERNS


class ClaimsGuardError(ValueError):
    """Raised when generated content contains prohibited claims."""
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__(f"Content rejected — prohibited claims detected: {violations}")


def check_claims(text: str) -> None:
    """
    Check text for prohibited claims. Raises ClaimsGuardError if any found.
    Call this on every AI-generated output before saving or displaying.
    """
    violations = []
    for pattern in _ALL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            violations.append(f"Pattern '{pattern}' matched: {matches[:2]}")

    if violations:
        raise ClaimsGuardError(violations)


def is_safe(text: str) -> tuple[bool, list[str]]:
    """
    Non-raising version. Returns (is_safe, violations).
    """
    try:
        check_claims(text)
        return True, []
    except ClaimsGuardError as e:
        return False, e.violations

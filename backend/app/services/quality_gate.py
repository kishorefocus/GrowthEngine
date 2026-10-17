"""
Quality gate for Programmatic SEO pages.
Ensures every page:
1. Exceeds 600 words.
2. Has less than 70% token/content similarity with existing pages.
3. Contains unique local or niche detail.
4. Passes claims_guard.
Calculates a quality_score (0.0 to 100.0).
"""
import re
from typing import Any, Sequence

from app.services.claims_guard import is_safe


def extract_full_text(content: dict[str, Any]) -> str:
    """Extract all readable text from a structured SEO content JSON."""
    parts = []
    if "title" in content:
        parts.append(str(content["title"]))
    if "h1" in content:
        parts.append(str(content["h1"]))
    if "intro" in content:
        parts.append(str(content["intro"]))

    for section in content.get("sections", []):
        if isinstance(section, dict):
            parts.append(str(section.get("heading", "")))
            parts.append(str(section.get("content", "")))

    for faq in content.get("faq", []):
        if isinstance(faq, dict):
            parts.append(str(faq.get("question", "")))
            parts.append(str(faq.get("answer", "")))

    comp = content.get("comparison_table")
    if isinstance(comp, dict):
        for feat in comp.get("features", []):
            if isinstance(feat, dict):
                parts.append(f"{feat.get('feature', '')}: {feat.get('globalreach', '')} vs {feat.get('competitor', '')}")

    return " ".join(parts)


def tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase alphanumeric words, filtering out short stopwords."""
    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "are", "have",
        "you", "your", "our", "all", "can", "will", "more", "their", "about"
    }
    return {w for w in words if w not in stopwords}


def calculate_jaccard_similarity(tokens_a: set[str], tokens_b: set[str]) -> float:
    """Calculate Jaccard similarity coefficient between two sets of word tokens."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


def check_niche_or_local_detail(text: str, variables: dict[str, Any]) -> bool:
    """Check that key variables (city, industry, competitor, niche) appear meaningfully in the content."""
    text_lower = text.lower()
    var_values = [
        str(v).lower().strip()
        for k, v in variables.items()
        if isinstance(v, (str, int)) and len(str(v).strip()) > 2
    ]
    if not var_values:
        return True

    # At least 80% of variable terms must appear in the text
    matches = sum(1 for val in var_values if val in text_lower)
    return (matches / len(var_values)) >= 0.75


def evaluate_seo_page(
    content: dict[str, Any],
    variables: dict[str, Any],
    existing_page_texts: Sequence[str] = (),
) -> dict[str, Any]:
    """
    Evaluate an SEO page candidate against the quality gate.
    
    Returns:
        dict:
            passed: bool
            quality_score: float (0.0 to 100.0)
            word_count: int
            max_similarity: float
            reasons: list[str]
            claims_violations: list[str]
    """
    full_text = extract_full_text(content)
    words = full_text.split()
    word_count = len(words)
    tokens = tokenize(full_text)

    reasons: list[str] = []
    score = 70.0

    # 1. Claims guard check
    claims_ok, violations = is_safe(full_text)
    if not claims_ok:
        reasons.append(f"Claims guard failed: {', '.join(violations[:2])}")
        score -= 40.0

    # 2. Word count check (minimum 600 words)
    if word_count < 600:
        reasons.append(f"Thin content: {word_count} words (minimum 600 required)")
        score -= 35.0
    elif word_count >= 1000:
        score += 15.0
    elif word_count >= 750:
        score += 10.0

    # 3. Similarity check (< 70% allowed)
    max_sim = 0.0
    for prev_text in existing_page_texts:
        prev_tokens = tokenize(prev_text)
        sim = calculate_jaccard_similarity(tokens, prev_tokens)
        if sim > max_sim:
            max_sim = sim

    if max_sim > 0.70:
        reasons.append(f"High similarity ({round(max_sim * 100, 1)}%) to existing pages (max 70% allowed)")
        score -= 40.0
    elif max_sim < 0.40 and existing_page_texts:
        score += 5.0

    # 4. Niche / local detail check
    has_niche_detail = check_niche_or_local_detail(full_text, variables)
    if not has_niche_detail:
        reasons.append("Missing required niche or local variable detail in page body")
        score -= 20.0
    else:
        score += 5.0

    # 5. Structure bonuses
    if len(content.get("faq", [])) >= 3:
        score += 3.0
    if content.get("comparison_table") and content["comparison_table"].get("features"):
        score += 2.0

    final_score = max(0.0, min(100.0, round(score, 1)))
    passed = word_count >= 600 and max_sim <= 0.70 and has_niche_detail and claims_ok and final_score >= 65.0

    return {
        "passed": passed,
        "quality_score": final_score,
        "word_count": word_count,
        "max_similarity": round(max_sim, 3),
        "reasons": reasons,
        "claims_violations": violations,
    }

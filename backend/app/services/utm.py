"""
UTM service: builds UTM-tagged links for all outbound channels.
utm_source, utm_medium, utm_campaign, utm_content
"""
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs, urljoin
from typing import Optional


def build_utm_url(
    base_url: str,
    source: str,
    medium: str,
    campaign: str,
    content: Optional[str] = None,
    term: Optional[str] = None,
) -> str:
    """
    Append UTM parameters to a URL.
    Preserves any existing query params.
    """
    parsed = urlparse(base_url)
    existing_params = parse_qs(parsed.query, keep_blank_values=True)

    utm_params: dict[str, str] = {
        "utm_source": source,
        "utm_medium": medium,
        "utm_campaign": campaign,
    }
    if content:
        utm_params["utm_content"] = content
    if term:
        utm_params["utm_term"] = term

    # Merge, UTM takes precedence
    merged = {k: v[0] for k, v in existing_params.items()}
    merged.update(utm_params)

    new_query = urlencode(merged)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def utm_dict(
    source: str,
    medium: str,
    campaign: str,
    content: Optional[str] = None,
) -> dict:
    """Return a UTM parameter dict for storing in JSONB columns."""
    result = {
        "utm_source": source,
        "utm_medium": medium,
        "utm_campaign": campaign,
    }
    if content:
        result["utm_content"] = content
    return result


# Canonical channel sources
CHANNELS = {
    "email": ("email", "cold_outreach"),
    "x": ("x", "social"),
    "linkedin": ("linkedin", "social"),
    "instagram": ("instagram", "social"),
    "facebook": ("facebook", "social"),
    "youtube": ("youtube", "video"),
    "seo": ("organic", "seo"),
    "tools": ("tools", "free_tool"),
    "product_hunt": ("product_hunt", "launch"),
    "reddit": ("reddit", "community"),
    "indiehackers": ("indiehackers", "community"),
}

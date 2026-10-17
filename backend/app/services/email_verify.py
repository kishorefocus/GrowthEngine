"""
Email verification service.
Performs: syntax check, MX record lookup, disposable domain detection, role-account detection.
SMTP-RCPT probing is intentionally excluded (provider-hostile, triggers blocks).
"""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ─── Disposable domain blocklist (expanded) ───────────────────────────────────

DISPOSABLE_DOMAINS: set[str] = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "sharklasers.com", "guerrillamailblock.com", "grr.la", "guerrillamail.info",
    "guerrillamail.biz", "guerrillamail.de", "guerrillamail.net", "guerrillamail.org",
    "spam4.me", "yopmail.com", "yopmail.fr", "cool.fr.nf", "jetable.fr.nf",
    "nospam.ze.tc", "nomail.xl.cx", "mega.zik.dj", "speed.1s.fr", "courriel.fr.nf",
    "moncourrier.fr.nf", "monemail.fr.nf", "monmail.fr.nf", "trashmail.com",
    "trashmail.me", "trashmail.net", "trashmail.org", "trashmail.at",
    "dispostable.com", "maildrop.cc", "mailnull.com", "spamgourmet.com",
    "10minutemail.com", "20minutemail.com", "tempinbox.com", "fakeinbox.com",
    "throwam.com", "mailnesia.com", "mailnull.com", "spamfree24.org",
    "discard.email", "spamherelots.com", "burnermail.io", "getairmail.com",
    "filzmail.com", "drdrb.com", "trashdevil.com",
}

# ─── Role-based prefixes ──────────────────────────────────────────────────────

ROLE_PREFIXES: set[str] = {
    "info", "sales", "admin", "support", "help", "contact", "hello", "team",
    "office", "billing", "accounts", "finance", "noreply", "no-reply",
    "postmaster", "webmaster", "abuse", "legal", "privacy", "security",
    "marketing", "hr", "jobs", "careers", "press", "media", "service",
    "general", "enquiries", "inquiry",
}


def _extract_parts(email: str) -> tuple[str, str]:
    """Return (local_part, domain) from a raw email string."""
    parts = email.lower().strip().rsplit("@", 1)
    if len(parts) != 2:
        return email.lower(), ""
    return parts[0], parts[1]


async def verify_email(email: str) -> dict[str, Any]:
    """
    Run all non-intrusive verification checks on an email address.

    Returns a dict with:
        - syntax_ok: bool
        - mx_ok: bool
        - is_disposable: bool
        - is_role: bool
        - status: "valid" | "invalid" | "risky"
        - notes: list[str]
    """
    notes: list[str] = []
    local, domain = _extract_parts(email)

    # 1. Syntax check
    syntax_ok = bool(re.match(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
        r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$",
        email.strip()
    ))
    if not syntax_ok:
        notes.append("Invalid email syntax")

    # 2. MX check
    mx_ok = False
    if syntax_ok and domain:
        try:
            import dns.asyncresolver
            answers = await dns.asyncresolver.resolve(domain, "MX")
            mx_ok = len(answers) > 0
        except Exception as exc:
            logger.debug("MX lookup failed for %s: %s", domain, exc)
            notes.append(f"No MX record found for {domain}")

    # 3. Disposable domain check
    is_disposable = domain in DISPOSABLE_DOMAINS
    if is_disposable:
        notes.append(f"Disposable domain: {domain}")

    # 4. Role-account check
    is_role = local in ROLE_PREFIXES
    if is_role:
        notes.append(f"Role account prefix: {local}")

    # Determine overall status
    if not syntax_ok or not mx_ok:
        status = "invalid"
    elif is_disposable or is_role:
        status = "risky"
    else:
        status = "valid"

    return {
        "syntax_ok": syntax_ok,
        "mx_ok": mx_ok,
        "is_disposable": is_disposable,
        "is_role": is_role,
        "status": status,
        "notes": notes,
    }

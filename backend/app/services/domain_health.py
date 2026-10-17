"""
Domain health service: checks SPF, DKIM, DMARC DNS records and returns
pass/fail with fix hints. Also provides a warm-up schedule suggestion.
Uses dnspython (dns.resolver).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _check_result(has_record: bool, hint_fail: str, hint_ok: str = "") -> dict:
    return {
        "status": "pass" if has_record else "fail",
        "hint": hint_ok if has_record else hint_fail,
    }


async def _query_txt(domain: str, prefix: str = "") -> list[str]:
    """Return all TXT records for a domain (or prefixed subdomain)."""
    try:
        import dns.asyncresolver
        target = f"{prefix}.{domain}" if prefix else domain
        answers = await dns.asyncresolver.resolve(target, "TXT")
        return [b.decode() for rdata in answers for b in rdata.strings]
    except Exception:
        return []


async def check_domain_health(domain: str, dkim_selector: str = "default") -> dict:
    """
    Check SPF, DKIM and DMARC records for the given domain.

    Returns a dict with:
        domain, spf, dkim, dmarc, overall, warmup_schedule
    """
    # SPF: look for a TXT record starting with "v=spf1"
    spf_records = await _query_txt(domain)
    spf_record = next((r for r in spf_records if r.startswith("v=spf1")), None)
    spf = {
        "status": "pass" if spf_record else "fail",
        "record": spf_record,
        "hint": (
            "SPF record found."
            if spf_record
            else f'Add a TXT record to {domain}: v=spf1 include:your-provider.com ~all'
        ),
    }

    # DKIM: look for TXT record at {selector}._domainkey.{domain}
    dkim_records = await _query_txt(domain, prefix=f"{dkim_selector}._domainkey")
    dkim_record = next((r for r in dkim_records if "v=DKIM1" in r), None)
    dkim = {
        "status": "pass" if dkim_record else "fail",
        "record": dkim_record,
        "selector": dkim_selector,
        "hint": (
            f"DKIM record found (selector={dkim_selector})."
            if dkim_record
            else (
                f"Add a TXT record to {dkim_selector}._domainkey.{domain} with your DKIM public key. "
                "Obtain it from your email provider dashboard."
            )
        ),
    }

    # DMARC: look for TXT record at _dmarc.{domain}
    dmarc_records = await _query_txt(domain, prefix="_dmarc")
    dmarc_record = next((r for r in dmarc_records if r.startswith("v=DMARC1")), None)
    dmarc = {
        "status": "pass" if dmarc_record else "fail",
        "record": dmarc_record,
        "hint": (
            "DMARC record found."
            if dmarc_record
            else (
                f'Add a TXT record to _dmarc.{domain}: '
                f'v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@{domain}'
            )
        ),
    }

    passing = sum(1 for c in [spf, dkim, dmarc] if c["status"] == "pass")
    if passing == 3:
        overall = "pass"
    elif passing >= 1:
        overall = "warn"
    else:
        overall = "fail"

    warmup_schedule = [
        {"week": 1, "daily_limit": 10, "note": "Establish sender reputation. Monitor for bounces."},
        {"week": 2, "daily_limit": 20, "note": "Double volume if bounce rate < 2%."},
        {"week": 3, "daily_limit": 40, "note": "Continue ramping if complaint rate < 0.1%."},
        {"week": 4, "daily_limit": 75, "note": "Approach normal volume."},
        {"week": 5, "daily_limit": 150, "note": "Full ramp. Monitor daily."},
        {"week": 6, "daily_limit": 300, "note": "Production volume. Keep bounce < 5%, complaints < 0.3%."},
    ]

    return {
        "domain": domain,
        "spf": spf,
        "dkim": dkim,
        "dmarc": dmarc,
        "overall": overall,
        "warmup_schedule": warmup_schedule,
    }

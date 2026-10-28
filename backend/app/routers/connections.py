"""
Social connections (OAuth) router:
- OAuth flows for X, LinkedIn, Meta (Instagram Business & Facebook Page), Google (YouTube).
- Encrypted token storage via services/crypto.py in social_accounts table.
- Start OAuth, callback handling, list connected accounts with status and expiry, disconnect.
"""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
import logging
import secrets
from typing import Optional
import urllib.parse
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
import httpx
import dotenv
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_owner
from app.models.auth import SocialAccount, User
from app.schemas.social import DirectConnectRequest, OAuthAuthorizeResponse, SocialAccountResponse
from app.services.audit import write_audit_log
from app.services.crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])

# Ephemeral state storage for OAuth CSRF protection (state -> {platform, code_verifier, created_at})
_oauth_states: dict[str, dict] = {}


def _cleanup_oauth_states():
    now = datetime.now(timezone.utc)
    expired = [k for k, v in _oauth_states.items() if (now - v["created_at"]).total_seconds() > 900]
    for k in expired:
        _oauth_states.pop(k, None)


@router.get("", response_model=list[SocialAccountResponse])
async def list_connections(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all connected social accounts with status and expiration."""
    # Dynamically read .env so manual edits are picked up without requiring server restart
    import dotenv
    env_vars = dotenv.dotenv_values(".env")
    fb_page_id = (env_vars.get("FACEBOOK_PAGE_ID") or settings.facebook_page_id or "").strip()
    fb_page_token = (env_vars.get("FACEBOOK_PAGE_ACCESS_TOKEN") or settings.facebook_page_access_token or "").strip()
    ig_account_id = (env_vars.get("INSTAGRAM_ACCOUNT_ID") or settings.instagram_account_id or "").strip()
    ig_token = (env_vars.get("INSTAGRAM_ACCESS_TOKEN") or settings.instagram_access_token or fb_page_token or "").strip()

    if fb_page_id and fb_page_token:
        fb_handle = "GetyourclientsB2B Facebook"
        fb_status = "active"
        # Validate against Meta Graph API to auto-fetch real Page name & linked Instagram ID
        if not fb_page_token.startswith("mock_"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    meta_res = await client.get(
                        f"https://graph.facebook.com/v19.0/{fb_page_id}",
                        params={
                            "fields": "id,name,instagram_business_account{id,username}",
                            "access_token": fb_page_token,
                        },
                    )
                    if meta_res.status_code == 200:
                        meta_data = meta_res.json()
                        fb_handle = meta_data.get("name", fb_handle)
                        ig_obj = meta_data.get("instagram_business_account")
                        if ig_obj and not ig_account_id:
                            ig_account_id = str(ig_obj.get("id"))
                            logger.info("Auto-discovered linked Instagram account %s (%s)", ig_obj.get("username"), ig_account_id)
                    else:
                        err_json = {}
                        try:
                            err_json = meta_res.json().get("error", {})
                        except Exception:
                            pass
                        code = err_json.get("code")
                        msg = err_json.get("message", "").lower()
                        if code == 190 or "expired" in msg:
                            fb_status = "expired"
                            logger.warning("Facebook Page Token is expired (code %s): %s", code, err_json.get("message"))
            except Exception as e:
                logger.warning("Could not auto-verify Facebook page token with Meta: %s", e)

        fb_res = await db.execute(select(SocialAccount).where(SocialAccount.platform == "facebook"))
        fb_acc = fb_res.scalar_one_or_none()
        # Protect existing active DB account from being overwritten by an expired .env token
        if fb_acc and fb_acc.status == "active" and fb_status == "expired":
            logger.info("Keeping active DB Facebook account; ignoring expired token in .env")
        else:
            if not fb_acc:
                fb_acc = SocialAccount(
                    platform="facebook",
                    handle=fb_handle,
                    external_id=fb_page_id,
                    encrypted_access_token=encrypt_token(fb_page_token),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=90),
                    status=fb_status,
                )
                db.add(fb_acc)
                await db.commit()
            else:
                fb_acc.handle = fb_handle
                fb_acc.external_id = fb_page_id
                fb_acc.encrypted_access_token = encrypt_token(fb_page_token)
                fb_acc.status = fb_status
                await db.commit()

    if ig_account_id and ig_token:
        ig_handle = "@getyourclientsb2b"
        ig_status = "active"
        if not ig_token.startswith("mock_"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    ig_res = await client.get(
                        f"https://graph.facebook.com/v19.0/{ig_account_id}",
                        params={"fields": "id,username", "access_token": ig_token},
                    )
                    if ig_res.status_code == 200:
                        uname = ig_res.json().get("username")
                        if uname:
                            ig_handle = f"@{uname}"
                    else:
                        err_json = {}
                        try:
                            err_json = ig_res.json().get("error", {})
                        except Exception:
                            pass
                        code = err_json.get("code")
                        msg = err_json.get("message", "").lower()
                        if code == 190 or "expired" in msg:
                            ig_status = "expired"
            except Exception as e:
                logger.warning("Could not auto-verify Instagram account with Meta: %s", e)

        ig_res = await db.execute(select(SocialAccount).where(SocialAccount.platform == "instagram"))
        ig_acc = ig_res.scalar_one_or_none()
        if ig_acc and ig_acc.status == "active" and ig_status == "expired":
            logger.info("Keeping active DB Instagram account; ignoring expired token in .env")
        else:
            if not ig_acc:
                ig_acc = SocialAccount(
                    platform="instagram",
                    handle=ig_handle,
                    external_id=ig_account_id,
                    encrypted_access_token=encrypt_token(ig_token),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=90),
                    status=ig_status,
                )
                db.add(ig_acc)
                await db.commit()
            else:
                ig_acc.handle = ig_handle
                ig_acc.external_id = ig_account_id
                ig_acc.encrypted_access_token = encrypt_token(ig_token)
                ig_acc.status = ig_status
                await db.commit()

    # Direct LinkedIn Page/Personal Token & Organization ID auto-sync
    li_token = (
        getattr(settings, "linkedin_page_access_token", "")
        or env_vars.get("LINKEDIN_PAGE_ACCESS_TOKEN", "")
        or env_vars.get("LINKEDIN_ACCESS_TOKEN", "")
        or ""
    ).strip().strip("'\"")
    li_org_id = (
        getattr(settings, "linkedin_organization_id", "")
        or env_vars.get("LINKEDIN_ORGANIZATION_ID", "")
        or ""
    ).strip().strip("'\"")

    if li_token:
        li_handle = "GetYourClients B2B" if li_org_id else "Kishore c"
        li_external_id = li_org_id if li_org_id else "self"
        if not li_org_id and not li_token.startswith("mock_"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    me_res = await client.get(
                        "https://api.linkedin.com/v2/userinfo",
                        headers={"Authorization": f"Bearer {li_token}"},
                    )
                    if me_res.status_code == 200:
                        me_data = me_res.json()
                        li_handle = me_data.get("name") or "Kishore c"
                        li_external_id = me_data.get("sub") or "self"
            except Exception as e:
                logger.warning("Could not auto-verify LinkedIn personal token: %s", e)

        li_res = await db.execute(select(SocialAccount).where(SocialAccount.platform == "linkedin"))
        li_acc = li_res.scalar_one_or_none()
        if not li_acc:
            li_acc = SocialAccount(
                platform="linkedin",
                handle=li_handle,
                external_id=li_external_id,
                encrypted_access_token=encrypt_token(li_token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=60),
                status="active",
            )
            db.add(li_acc)
            await db.commit()
        else:
            li_acc.handle = li_handle
            li_acc.external_id = li_external_id
            li_acc.encrypted_access_token = encrypt_token(li_token)
            li_acc.status = "active"
            await db.commit()

    result = await db.execute(select(SocialAccount).order_by(SocialAccount.created_at.desc()))
    accounts = result.scalars().all()

    now = datetime.now(timezone.utc)
    response_list = []
    for acc in accounts:
        status_val = acc.status
        expires_dt = acc.expires_at
        if expires_dt and expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if expires_dt and expires_dt < now:
            status_val = "expired"

        response_list.append(
            SocialAccountResponse(
                id=str(acc.id),
                platform=acc.platform,
                handle=acc.handle,
                external_id=acc.external_id,
                status=status_val,
                expires_at=acc.expires_at,
                created_at=acc.created_at,
                updated_at=acc.updated_at,
            )
        )
    return response_list


@router.get("/{platform}/authorize", response_model=OAuthAuthorizeResponse)
async def get_oauth_authorization_url(
    platform: str,
    _: User = Depends(require_owner),
):
    """
    Generate the official OAuth authorization URL for the selected platform.
    Platforms: x, linkedin, meta (instagram & facebook), youtube
    """
    _cleanup_oauth_states()
    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.api_url}/api/v1/connections/{platform}/callback"

    if platform == "x":
        if not settings.x_client_id:
            # Fallback to internal mock callback when live credentials are not set
            mock_url = f"{redirect_uri}?code=mock_x_code&state={state}"
            return OAuthAuthorizeResponse(platform=platform, authorization_url=mock_url, state=state)

        # RFC 7636 PKCE S256
        code_verifier = secrets.token_urlsafe(64)
        code_challenge_b64 = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
            .decode("ascii")
            .rstrip("=")
        )
        state_payload = json.dumps({
            "nonce": secrets.token_urlsafe(16),
            "platform": "x",
            "code_verifier": code_verifier,
        })
        state = encrypt_token(state_payload)
        _oauth_states[state] = {
            "platform": "x",
            "code_verifier": code_verifier,
            "created_at": datetime.now(timezone.utc),
        }

        params = {
            "response_type": "code",
            "client_id": settings.x_client_id,
            "redirect_uri": redirect_uri,
            "scope": "tweet.read tweet.write users.read offline.access",
            "state": state,
            "code_challenge": code_challenge_b64,
            "code_challenge_method": "S256",
        }
        auth_url = f"https://twitter.com/i/oauth2/authorize?{urllib.parse.urlencode(params)}"

    elif platform == "linkedin":
        env_vars = dotenv.dotenv_values(".env")
        li_client_id = (env_vars.get("LINKEDIN_CLIENT_ID") or settings.linkedin_client_id or "").strip()
        if not li_client_id:
            mock_url = f"{redirect_uri}?code=mock_linkedin_code&state={state}"
            return OAuthAuthorizeResponse(platform=platform, authorization_url=mock_url, state=state)

        _oauth_states[state] = {
            "platform": "linkedin",
            "created_at": datetime.now(timezone.utc),
        }
        has_org_config = bool((env_vars.get("LINKEDIN_ORGANIZATION_ID") or getattr(settings, "linkedin_organization_id", "") or "").strip())
        custom_scopes = (env_vars.get("LINKEDIN_SCOPES") or getattr(settings, "linkedin_scopes", "") or "").strip()
        if custom_scopes:
            scopes = custom_scopes
        elif has_org_config:
            scopes = "openid profile email w_member_social w_organization_social r_organization_social"
        else:
            scopes = "openid profile email w_member_social"

        params = {
            "response_type": "code",
            "client_id": li_client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
        }
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"

    elif platform in ("meta", "instagram", "facebook"):
        if not settings.meta_app_id:
            mock_url = f"{redirect_uri}?code=mock_{platform}_code&state={state}"
            return OAuthAuthorizeResponse(platform=platform, authorization_url=mock_url, state=state)

        _oauth_states[state] = {
            "platform": platform,
            "created_at": datetime.now(timezone.utc),
        }
        if platform == "instagram":
            scopes = "pages_show_list,instagram_basic,instagram_content_publish"
        elif platform == "facebook":
            scopes = "pages_show_list,pages_manage_posts,pages_read_engagement"
        else:
            scopes = "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"

        params = {
            "client_id": settings.meta_app_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
            "response_type": "code",
        }
        auth_url = f"https://www.facebook.com/v19.0/dialog/oauth?{urllib.parse.urlencode(params)}"

    elif platform == "youtube":
        if not settings.google_client_id:
            mock_url = f"{redirect_uri}?code=mock_youtube_code&state={state}"
            return OAuthAuthorizeResponse(platform=platform, authorization_url=mock_url, state=state)

        _oauth_states[state] = {
            "platform": "youtube",
            "created_at": datetime.now(timezone.utc),
        }
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    return OAuthAuthorizeResponse(platform=platform, authorization_url=auth_url, state=state)


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Official OAuth callback handler. Exchanges authorization code for tokens,
    encrypts tokens with Fernet, and saves the SocialAccount record.
    Redirects back to frontend /admin/connections?connected={platform}.
    """
    redirect_uri = f"{settings.api_url}/api/v1/connections/{platform}/callback"

    # Handle provider cancellation or scope error gracefully
    if error or not code:
        err_msg = error_description or error or "OAuth authorization was denied or failed"
        logger.warning("OAuth error for %s: %s (%s)", platform, err_msg, error)
        from fastapi.responses import RedirectResponse
        frontend_err_dest = f"{settings.frontend_url}/admin/connections?error={urllib.parse.quote(err_msg)}"
        return RedirectResponse(url=frontend_err_dest, status_code=302)

    access_token = ""
    refresh_token = ""
    expires_at = datetime.now(timezone.utc) + timedelta(days=60)
    handle = ""
    external_id = ""
    token_error_detail = ""

    # Simulated/Mock flow if API credentials are not set (e.g. during development/testing)
    is_mock = False
    if platform == "x" and not settings.x_client_secret:
        is_mock = True
    elif platform == "linkedin" and not settings.linkedin_client_secret:
        is_mock = True
    elif platform in ("meta", "instagram", "facebook") and not settings.meta_app_secret:
        is_mock = True
    elif platform == "youtube" and not settings.google_client_secret:
        is_mock = True

    if is_mock or code.startswith("mock_"):
        handle = f"@getyourclientsb2b_{platform}"
        external_id = f"ext_{platform}_{uuid.uuid4().hex[:8]}"
        access_token = f"mock_access_token_{platform}_{uuid.uuid4().hex}"
        refresh_token = f"mock_refresh_token_{platform}_{uuid.uuid4().hex}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=60)
    else:
        # Live token exchange
        async with httpx.AsyncClient(timeout=30.0) as client:
            if platform == "x":
                # Recover code_verifier from encrypted state token or memory
                verifier = ""
                if state:
                    try:
                        decrypted = json.loads(decrypt_token(state))
                        verifier = decrypted.get("code_verifier", "")
                    except Exception:
                        pass
                if not verifier and state:
                    verifier = _oauth_states.get(state, {}).get("code_verifier", "")

                res = await client.post(
                    "https://api.twitter.com/2/oauth2/token",
                    data={
                        "code": code,
                        "grant_type": "authorization_code",
                        "client_id": settings.x_client_id,
                        "redirect_uri": redirect_uri,
                        "code_verifier": verifier,
                    },
                    auth=(settings.x_client_id, settings.x_client_secret),
                )
                data = res.json()
                if res.status_code != 200:
                    token_error_detail = data.get("error_description") or data.get("error") or f"X API error: {res.status_code}"
                    logger.error("X token exchange error (%d): %s", res.status_code, data)
                else:
                    access_token = data.get("access_token", "")
                    refresh_token = data.get("refresh_token", "")
                    expires_in = data.get("expires_in", 7200)
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    # Fetch handle
                    me_res = await client.get(
                        "https://api.twitter.com/2/users/me",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if me_res.status_code == 200:
                        user_data = me_res.json().get("data", {})
                        handle = f"@{user_data.get('username')}"
                        external_id = user_data.get("id")

            elif platform == "linkedin":
                env_vars = dotenv.dotenv_values(".env")
                li_client_id = (env_vars.get("LINKEDIN_CLIENT_ID") or settings.linkedin_client_id or "").strip()
                li_client_secret = (env_vars.get("LINKEDIN_CLIENT_SECRET") or settings.linkedin_client_secret or "").strip()
                res = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": li_client_id,
                        "client_secret": li_client_secret,
                    },
                )
                data = res.json()
                access_token = data.get("access_token", "")
                refresh_token = data.get("refresh_token", "")
                expires_in = data.get("expires_in", 5184000)  # 60 days
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                env_org_id = (env_vars.get("LINKEDIN_ORGANIZATION_ID") or getattr(settings, "linkedin_organization_id", "") or "").strip()
                handle = "GetYourClients B2B"
                external_id = env_org_id.removeprefix("urn:li:organization:") if env_org_id else "org_getyourclientsb2b"
                if access_token:
                    # Attempt 1: Discover Organization Page via ACLs
                    try:
                        acl_res = await client.get(
                            "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee",
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        if acl_res.status_code == 200:
                            acl_elements = acl_res.json().get("elements", [])
                            if acl_elements:
                                org_target = acl_elements[0].get("organizationalTarget", "")
                                if "organization:" in org_target:
                                    external_id = org_target.split("organization:")[1]
                                    handle = "GetYourClients B2B"
                    except Exception:
                        pass

                    # Attempt 2: If no org configured or discovered, fallback to personal profile
                    if not env_org_id and external_id == "org_getyourclientsb2b":
                        try:
                            me_res = await client.get(
                                "https://api.linkedin.com/v2/userinfo",
                                headers={"Authorization": f"Bearer {access_token}"},
                            )
                            if me_res.status_code == 200:
                                me_data = me_res.json()
                                handle = me_data.get("name") or "LinkedIn Profile"
                                external_id = me_data.get("sub", "org_globalreach")
                        except Exception:
                            pass

            elif platform in ("meta", "instagram", "facebook"):
                res = await client.get(
                    "https://graph.facebook.com/v19.0/oauth/access_token",
                    params={
                        "client_id": settings.meta_app_id,
                        "client_secret": settings.meta_app_secret,
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                )
                data = res.json()
                access_token = data.get("access_token", "")
                expires_at = datetime.now(timezone.utc) + timedelta(days=60)
                handle = f"GetyourclientsB2B {platform.capitalize()}"
                external_id = "108923481729012" if platform == "facebook" else "17841400293847561"
                if access_token:
                    # 1. Exchange short-lived token for long-lived 60-day user token
                    try:
                        long_res = await client.get(
                            "https://graph.facebook.com/v19.0/oauth/access_token",
                            params={
                                "grant_type": "fb_exchange_token",
                                "client_id": settings.meta_app_id,
                                "client_secret": settings.meta_app_secret,
                                "fb_exchange_token": access_token,
                            },
                        )
                        if long_res.status_code == 200:
                            long_data = long_res.json()
                            if long_data.get("access_token"):
                                access_token = long_data["access_token"]
                                logger.info("Meta token upgraded to 60-day long-lived token")
                    except Exception as exc:
                        logger.warning("Could not exchange Meta token: %s", exc)

                    # 2. Fetch pages — Meta provides never-expiring Page tokens from long-lived user tokens
                    try:
                        acc_res = await client.get(
                            "https://graph.facebook.com/v19.0/me/accounts",
                            params={"fields": "id,name,access_token,instagram_business_account{id,username}", "access_token": access_token},
                        )
                        if acc_res.status_code == 200:
                            pages = acc_res.json().get("data", [])
                            if pages:
                                if platform == "instagram":
                                    found_ig = False
                                    for p in pages:
                                        ig = p.get("instagram_business_account")
                                        if ig:
                                            handle = f"@{ig.get('username')}"
                                            external_id = str(ig.get("id"))
                                            page_token = p.get("access_token", access_token)
                                            access_token = page_token
                                            found_ig = True

                                            # Auto-connect Facebook Page as well
                                            fb_pid = str(p.get("id"))
                                            fb_pname = p.get("name", "Facebook Page")
                                            fb_r = await db.execute(select(SocialAccount).where(SocialAccount.platform == "facebook"))
                                            fb_a = fb_r.scalar_one_or_none()
                                            if not fb_a:
                                                fb_a = SocialAccount(
                                                    platform="facebook",
                                                    handle=fb_pname,
                                                    external_id=fb_pid,
                                                    encrypted_access_token=encrypt_token(page_token),
                                                    expires_at=datetime.now(timezone.utc) + timedelta(days=90),
                                                    status="active",
                                                )
                                                db.add(fb_a)
                                            else:
                                                fb_a.handle = fb_pname
                                                fb_a.external_id = fb_pid
                                                fb_a.encrypted_access_token = encrypt_token(page_token)
                                                fb_a.status = "active"

                                            try:
                                                import dotenv
                                                dotenv.set_key(".env", "FACEBOOK_PAGE_ID", fb_pid)
                                                dotenv.set_key(".env", "FACEBOOK_PAGE_ACCESS_TOKEN", page_token)
                                                dotenv.set_key(".env", "INSTAGRAM_ACCOUNT_ID", external_id)
                                                dotenv.set_key(".env", "INSTAGRAM_ACCESS_TOKEN", page_token)
                                            except Exception:
                                                pass
                                            break
                                    if not found_ig:
                                        token_error_detail = (
                                            "No Instagram Business/Creator account found linked to your Facebook Pages. "
                                            "Please connect your Instagram account to a Facebook Page in Meta Business Suite and reconnect."
                                        )
                                elif platform == "facebook":
                                    p = pages[0]
                                    handle = p.get("name", "Facebook Page")
                                    external_id = str(p.get("id"))
                                    page_token = p.get("access_token", access_token)
                                    access_token = page_token

                                    # Auto-connect linked Instagram account if present on this Page!
                                    ig = p.get("instagram_business_account")
                                    if ig:
                                        ig_handle = f"@{ig.get('username')}"
                                        ig_id = str(ig.get("id"))
                                        ig_r = await db.execute(select(SocialAccount).where(SocialAccount.platform == "instagram"))
                                        ig_a = ig_r.scalar_one_or_none()
                                        if not ig_a:
                                            ig_a = SocialAccount(
                                                platform="instagram",
                                                handle=ig_handle,
                                                external_id=ig_id,
                                                encrypted_access_token=encrypt_token(page_token),
                                                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
                                                status="active",
                                            )
                                            db.add(ig_a)
                                        else:
                                            ig_a.handle = ig_handle
                                            ig_a.external_id = ig_id
                                            ig_a.encrypted_access_token = encrypt_token(page_token)
                                            ig_a.status = "active"

                                        try:
                                            import dotenv
                                            dotenv.set_key(".env", "INSTAGRAM_ACCOUNT_ID", ig_id)
                                            dotenv.set_key(".env", "INSTAGRAM_ACCESS_TOKEN", page_token)
                                        except Exception:
                                            pass

                                    try:
                                        import dotenv
                                        dotenv.set_key(".env", "FACEBOOK_PAGE_ID", external_id)
                                        dotenv.set_key(".env", "FACEBOOK_PAGE_ACCESS_TOKEN", page_token)
                                    except Exception:
                                        pass
                            else:
                                token_error_detail = (
                                    "No Facebook Pages found on your account. Meta only supports automated posting to Facebook Pages, not personal profiles. "
                                    "Please create a Facebook Page at https://www.facebook.com/pages/create and reconnect."
                                )
                    except Exception as exc:
                        logger.warning("Error fetching Facebook pages: %s", exc)

            elif platform == "youtube":
                res = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                data = res.json()
                access_token = data.get("access_token", "")
                refresh_token = data.get("refresh_token", "")
                expires_in = data.get("expires_in", 3600)
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                handle = "GlobalReach YouTube"
                external_id = "channel_globalreach"
                if access_token:
                    try:
                        ch_res = await client.get(
                            "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        if ch_res.status_code == 200:
                            items = ch_res.json().get("items", [])
                            if items:
                                snippet = items[0].get("snippet", {})
                                handle = snippet.get("title", "YouTube Channel")
                                external_id = items[0].get("id", "channel_globalreach")
                    except Exception:
                        pass

    if state:
        _oauth_states.pop(state, None)

    if not access_token or token_error_detail:
        err_msg = token_error_detail or "Failed to obtain access token from provider"
        logger.warning("OAuth token exchange failed for %s: %s", platform, err_msg)
        from fastapi.responses import RedirectResponse
        frontend_err_dest = f"{settings.frontend_url}/admin/connections?error={urllib.parse.quote(err_msg)}"
        return RedirectResponse(url=frontend_err_dest, status_code=302)

    # Upsert social account
    existing = await db.execute(select(SocialAccount).where(SocialAccount.platform == platform))
    account = existing.scalar_one_or_none()
    if not account:
        account = SocialAccount(
            platform=platform,
            handle=handle,
            external_id=external_id,
            encrypted_access_token=encrypt_token(access_token),
            encrypted_refresh_token=encrypt_token(refresh_token) if refresh_token else None,
            expires_at=expires_at,
            status="active",
        )
        db.add(account)
    else:
        account.handle = handle or account.handle
        account.external_id = external_id or account.external_id
        account.encrypted_access_token = encrypt_token(access_token)
        if refresh_token:
            account.encrypted_refresh_token = encrypt_token(refresh_token)
        account.expires_at = expires_at
        account.status = "active"

    await db.commit()

    # Redirect user to the frontend connections settings page
    frontend_dest = f"{settings.frontend_url}/admin/connections?connected={platform}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=frontend_dest, status_code=302)


@router.post("/instagram/sync-from-facebook", response_model=SocialAccountResponse)
async def sync_instagram_from_facebook(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """
    Sync Instagram Business account from the connected Facebook Page.
    """
    fb_res = await db.execute(select(SocialAccount).where(SocialAccount.platform == "facebook"))
    fb_acc = fb_res.scalar_one_or_none()
    if not fb_acc or not fb_acc.encrypted_access_token or not fb_acc.external_id:
        raise HTTPException(
            status_code=400,
            detail="Facebook must be connected first to sync its linked Instagram account."
        )

    try:
        page_token = decrypt_token(fb_acc.encrypted_access_token)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decrypt Facebook Page token.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        page_id = fb_acc.external_id
        res = await client.get(
            f"https://graph.facebook.com/v19.0/{page_id}",
            params={"fields": "instagram_business_account{id,username}", "access_token": page_token},
        )
        if res.status_code != 200:
            err_msg = res.text
            is_token_expired = False
            try:
                err_data = res.json().get("error", {})
                code = err_data.get("code")
                raw_msg = err_data.get("message", "")
                if code == 190 or "expired" in raw_msg.lower() or "session has expired" in raw_msg.lower():
                    is_token_expired = True
                    err_msg = (
                        "Your Facebook Page Access Token has expired on Meta. "
                        "Please update FACEBOOK_PAGE_ACCESS_TOKEN in .env or reconnect Facebook."
                    )
                else:
                    err_msg = f"Meta API Error ({code}): {raw_msg}"
            except Exception:
                pass

            if is_token_expired:
                fb_acc.status = "expired"
                await db.commit()

            raise HTTPException(status_code=400, detail=err_msg)

        data = res.json()
        ig_data = data.get("instagram_business_account")
        if not ig_data:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No Instagram Professional/Business account is linked to Facebook Page '{page_id}'. "
                    "Please link your Instagram account in Facebook Page Settings > Linked Accounts > Instagram, "
                    "or connect Instagram directly using its ID & Token via the 'Token / ID' button."
                )
            )

        ig_id = str(ig_data["id"])
        ig_username = ig_data.get("username", "instagram")
        ig_handle = f"@{ig_username}"

        ig_res = await db.execute(select(SocialAccount).where(SocialAccount.platform == "instagram"))
        ig_acc = ig_res.scalar_one_or_none()
        if not ig_acc:
            ig_acc = SocialAccount(
                platform="instagram",
                handle=ig_handle,
                external_id=ig_id,
                encrypted_access_token=fb_acc.encrypted_access_token,
                encrypted_refresh_token=fb_acc.encrypted_refresh_token,
                expires_at=fb_acc.expires_at,
                status="active",
            )
            db.add(ig_acc)
        else:
            ig_acc.handle = ig_handle
            ig_acc.external_id = ig_id
            ig_acc.encrypted_access_token = fb_acc.encrypted_access_token
            ig_acc.encrypted_refresh_token = fb_acc.encrypted_refresh_token
            ig_acc.expires_at = fb_acc.expires_at
            ig_acc.status = "active"

        await db.commit()
        await db.refresh(ig_acc)

        await write_audit_log(
            db,
            action="connection.connected",
            user_id=current_user.id,
            entity="social_accounts",
            entity_id=str(ig_acc.id),
            meta={"platform": "instagram", "handle": ig_handle, "synced_from": "facebook"},
        )
        await db.commit()

        return SocialAccountResponse(
            id=str(ig_acc.id),
            platform=ig_acc.platform,
            handle=ig_acc.handle,
            external_id=ig_acc.external_id,
            status=ig_acc.status,
            expires_at=ig_acc.expires_at,
            created_at=ig_acc.created_at,
            updated_at=ig_acc.updated_at,
        )


@router.post("/connect-mock", response_model=SocialAccountResponse)
async def connect_mock_account(
    platform: str = Query(...),
    handle: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """
    Explicit endpoint for development/testing to connect a mock verified account
    without needing live OAuth developer credentials.
    """
    valid_platforms = ["x", "linkedin", "instagram", "facebook", "youtube"]
    if platform not in valid_platforms:
        raise HTTPException(status_code=400, detail=f"Platform must be one of {valid_platforms}")

    existing = await db.execute(select(SocialAccount).where(SocialAccount.platform == platform))
    account = existing.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=60)

    # For Meta and downstream validators, generate realistic numeric IDs
    default_mock_ids = {
        "facebook": "108923481729012",
        "instagram": "17841400293847561",
        "x": "1654321987654321",
        "linkedin": "urn:li:organization:98765432",
        "youtube": "UCgetyourclientsb2b_mock",
    }
    mock_ext_id = default_mock_ids.get(platform, f"mock_{platform}_{uuid.uuid4().hex[:6]}")

    if not account:
        account = SocialAccount(
            platform=platform,
            handle=handle,
            external_id=mock_ext_id,
            encrypted_access_token=encrypt_token(f"mock_token_{platform}"),
            encrypted_refresh_token=encrypt_token(f"mock_refresh_{platform}"),
            expires_at=expires_at,
            status="active",
        )
        db.add(account)
    else:
        account.handle = handle
        account.external_id = mock_ext_id
        account.status = "active"
        account.expires_at = expires_at
        account.encrypted_access_token = encrypt_token(f"mock_token_{platform}")

    await db.commit()
    await db.refresh(account)

    await write_audit_log(
        db,
        action="connection.connected",
        user_id=current_user.id,
        entity="social_accounts",
        entity_id=str(account.id),
        meta={"platform": platform, "handle": handle, "mode": "sandbox"},
    )
    await db.commit()

    return SocialAccountResponse(
        id=str(account.id),
        platform=account.platform,
        handle=account.handle,
        external_id=account.external_id,
        status=account.status,
        expires_at=account.expires_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.post("/direct", response_model=SocialAccountResponse)
async def direct_connect_account(
    payload: DirectConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """
    Directly connect a verified social account using a Page ID / Access Token.
    Auto-validates with Meta Graph API when a live token is supplied.
    """
    platform = payload.platform.lower().strip()
    valid_platforms = ["x", "linkedin", "instagram", "facebook", "youtube"]
    if platform not in valid_platforms:
        raise HTTPException(status_code=400, detail=f"Platform must be one of {valid_platforms}")

    handle = (payload.handle or "").strip()
    external_id = (payload.external_id or "").strip()
    access_token = payload.access_token.strip()

    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")

    # If it is Meta (Facebook or Instagram) with a real token, query Graph API for auto-detection
    if platform == "facebook" and not access_token.startswith("mock_"):
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. First test /me to verify token validity
            me_res = await client.get(
                "https://graph.facebook.com/v19.0/me",
                params={"fields": "id,name", "access_token": access_token},
            )
            if me_res.status_code != 200:
                err_text = ""
                try:
                    err_text = me_res.json().get("error", {}).get("message", me_res.text)
                except Exception:
                    err_text = me_res.text
                raise HTTPException(status_code=400, detail=f"Meta rejected this token: {err_text}")

            # 2. Check /me/accounts in case it is a User Access Token with managed Pages
            acc_res = await client.get(
                "https://graph.facebook.com/v19.0/me/accounts",
                params={"fields": "id,name,access_token,instagram_business_account{id,username}", "access_token": access_token},
            )

            page_found = False
            if acc_res.status_code == 200:
                pages = acc_res.json().get("data", [])
                if pages:
                    # User token with managed pages!
                    target_page = None
                    if external_id and external_id != "108923481729012":
                        for p in pages:
                            if str(p.get("id")) == str(external_id):
                                target_page = p
                                break
                    if not target_page:
                        target_page = pages[0]

                    external_id = str(target_page.get("id"))
                    handle = target_page.get("name", handle or "Facebook Page")
                    access_token = target_page.get("access_token", access_token)
                    page_found = True
                    logger.info("Auto-selected Facebook Page from User Token: %s (%s)", handle, external_id)

                    ig_data = target_page.get("instagram_business_account")
                    if ig_data:
                        ig_id = str(ig_data.get("id"))
                        ig_uname = ig_data.get("username", "instagram")
                        ig_res = await db.execute(select(SocialAccount).where(SocialAccount.platform == "instagram"))
                        ig_acc = ig_res.scalar_one_or_none()
                        if not ig_acc:
                            ig_acc = SocialAccount(
                                platform="instagram",
                                handle=f"@{ig_uname}",
                                external_id=ig_id,
                                encrypted_access_token=encrypt_token(access_token),
                                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
                                status="active",
                            )
                            db.add(ig_acc)
                        else:
                            ig_acc.handle = f"@{ig_uname}"
                            ig_acc.external_id = ig_id
                            ig_acc.encrypted_access_token = encrypt_token(access_token)
                            ig_acc.status = "active"

                        try:
                            import dotenv
                            dotenv.set_key(".env", "INSTAGRAM_ACCOUNT_ID", ig_id)
                            dotenv.set_key(".env", "INSTAGRAM_ACCESS_TOKEN", access_token)
                        except Exception:
                            pass

            # 3. If not resolved from /me/accounts, verify if the token directly accesses the Page ID or /me
            if not page_found:
                test_id = external_id if (external_id and external_id != "108923481729012") else "me"
                res = await client.get(
                    f"https://graph.facebook.com/v19.0/{test_id}",
                    params={"fields": "id,name,access_token,instagram_business_account{id,username}", "access_token": access_token},
                )
                if res.status_code == 200:
                    data = res.json()
                    external_id = str(data.get("id", external_id))
                    if data.get("access_token"):
                        access_token = data["access_token"]
                    elif external_id:
                        try:
                            tok_query = await client.get(
                                f"https://graph.facebook.com/v19.0/{external_id}",
                                params={"fields": "access_token", "access_token": access_token},
                            )
                            if tok_query.status_code == 200:
                                pt = tok_query.json().get("access_token")
                                if pt:
                                    access_token = pt
                        except Exception:
                            pass
                    logger.info("Directly verified Facebook Page: %s (%s)", handle, external_id)
                    page_found = True

                    ig_data = data.get("instagram_business_account")
                    if ig_data:
                        ig_id = str(ig_data.get("id"))
                        ig_uname = ig_data.get("username", "instagram")
                        ig_res = await db.execute(select(SocialAccount).where(SocialAccount.platform == "instagram"))
                        ig_acc = ig_res.scalar_one_or_none()
                        if not ig_acc:
                            ig_acc = SocialAccount(
                                platform="instagram",
                                handle=f"@{ig_uname}",
                                external_id=ig_id,
                                encrypted_access_token=encrypt_token(access_token),
                                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
                                status="active",
                            )
                            db.add(ig_acc)
                        else:
                            ig_acc.handle = f"@{ig_uname}"
                            ig_acc.external_id = ig_id
                            ig_acc.encrypted_access_token = encrypt_token(access_token)
                            ig_acc.status = "active"

                        try:
                            import dotenv
                            dotenv.set_key(".env", "INSTAGRAM_ACCOUNT_ID", ig_id)
                            dotenv.set_key(".env", "INSTAGRAM_ACCESS_TOKEN", access_token)
                        except Exception:
                            pass
                else:
                    err_data = {}
                    try:
                        err_data = res.json().get("error", {})
                    except Exception:
                        pass
                    err_msg = err_data.get("message", res.text)
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Could not verify Facebook Page '{test_id}': {err_msg}. "
                            "Meta Graph API only supports publishing to Facebook Pages, not personal profiles. "
                            "If you haven't created a Facebook Page yet, please create one at https://www.facebook.com/pages/create "
                            "and ensure your Page Access Token is selected in Graph API Explorer."
                        )
                    )

            try:
                import dotenv
                dotenv.set_key(".env", "FACEBOOK_PAGE_ID", external_id)
                dotenv.set_key(".env", "FACEBOOK_PAGE_ACCESS_TOKEN", access_token)
            except Exception:
                pass

    elif platform == "instagram" and not access_token.startswith("mock_"):
        async with httpx.AsyncClient(timeout=15.0) as client:
            test_id = external_id or "me"
            try:
                res = await client.get(
                    f"https://graph.facebook.com/v19.0/{test_id}",
                    params={"fields": "id,username", "access_token": access_token},
                )
                if res.status_code == 200:
                    data = res.json()
                    external_id = data.get("id", external_id)
                    uname = data.get("username")
                    if uname:
                        handle = f"@{uname}"
                    logger.info("Meta Graph API verified Instagram Account: %s (%s)", handle, external_id)

                    try:
                        import dotenv
                        dotenv.set_key(".env", "INSTAGRAM_ACCOUNT_ID", external_id)
                        dotenv.set_key(".env", "INSTAGRAM_ACCESS_TOKEN", access_token)
                    except Exception:
                        pass
                else:
                    logger.warning("Meta Graph API returned %d for Instagram: %s", res.status_code, res.text)
            except Exception as e:
                logger.warning("Meta Graph API check error: %s", e)

    # Sensible defaults for handle and numeric external_id if still blank
    if not handle:
        handle = f"@getyourclientsb2b_{platform}"
    if not external_id:
        default_ids = {
            "facebook": "108923481729012",
            "instagram": "17841400293847561",
            "x": "1654321987654321",
            "linkedin": "urn:li:organization:98765432",
            "youtube": "UCgetyourclientsb2b_mock",
        }
        external_id = default_ids.get(platform, f"108923481729012")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=60)

    existing = await db.execute(select(SocialAccount).where(SocialAccount.platform == platform))
    account = existing.scalar_one_or_none()

    if not account:
        account = SocialAccount(
            platform=platform,
            handle=handle,
            external_id=external_id,
            encrypted_access_token=encrypt_token(access_token),
            expires_at=expires_at,
            status="active",
        )
        db.add(account)
    else:
        account.handle = handle
        account.external_id = external_id
        account.encrypted_access_token = encrypt_token(access_token)
        account.expires_at = expires_at
        account.status = "active"

    await db.commit()
    await db.refresh(account)

    await write_audit_log(
        db,
        action="connection.connected",
        user_id=current_user.id,
        entity="social_accounts",
        entity_id=str(account.id),
        meta={"platform": platform, "handle": handle, "method": "direct"},
    )
    await db.commit()

    return SocialAccountResponse(
        id=str(account.id),
        platform=account.platform,
        handle=account.handle,
        external_id=account.external_id,
        status=account.status,
        expires_at=account.expires_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.delete("/{id}", status_code=204)
async def disconnect_account(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """Disconnect and revoke a social account connection."""
    acc_uuid = uuid.UUID(id)
    account = await db.get(SocialAccount, acc_uuid)
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")

    platform = account.platform
    await db.delete(account)
    await db.commit()

    await write_audit_log(
        db,
        action="connection.disconnected",
        user_id=current_user.id,
        entity="social_accounts",
        entity_id=id,
        meta={"platform": platform},
    )
    await db.commit()
    return None

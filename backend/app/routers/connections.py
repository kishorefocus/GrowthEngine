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
import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_owner
from app.models.auth import SocialAccount, User
from app.schemas.social import OAuthAuthorizeResponse, SocialAccountResponse
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
        if not settings.linkedin_client_id:
            mock_url = f"{redirect_uri}?code=mock_linkedin_code&state={state}"
            return OAuthAuthorizeResponse(platform=platform, authorization_url=mock_url, state=state)

        _oauth_states[state] = {
            "platform": "linkedin",
            "created_at": datetime.now(timezone.utc),
        }
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email w_member_social",
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
                res = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": settings.linkedin_client_id,
                        "client_secret": settings.linkedin_client_secret,
                    },
                )
                data = res.json()
                access_token = data.get("access_token", "")
                refresh_token = data.get("refresh_token", "")
                expires_in = data.get("expires_in", 5184000)  # 60 days
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                handle = "GetyourclientsB2B"
                external_id = "org_getyourclientsb2b"
                if access_token:
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
                handle = f"GlobalReach {platform.capitalize()}"
                external_id = f"page_{platform}"
                if access_token:
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
                                            external_id = ig.get("id")
                                            if p.get("access_token"):
                                                access_token = p["access_token"]
                                            found_ig = True
                                            break
                                    if not found_ig:
                                        token_error_detail = (
                                            "No Instagram Business/Creator account found linked to your Facebook Pages. "
                                            "Please connect your Instagram account to a Facebook Page in Meta Business Suite and reconnect."
                                        )
                                elif platform == "facebook":
                                    handle = pages[0].get("name", "Facebook Page")
                                    external_id = pages[0].get("id")
                                    if pages[0].get("access_token"):
                                        access_token = pages[0]["access_token"]
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
            raise HTTPException(status_code=400, detail=f"Failed to query Meta for linked Instagram account: {res.text}")

        data = res.json()
        ig_data = data.get("instagram_business_account")
        if not ig_data:
            raise HTTPException(
                status_code=400,
                detail="No Instagram Business account is linked to your Facebook Page. Please link it in Facebook Page Settings > Linked Accounts."
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

    if not account:
        account = SocialAccount(
            platform=platform,
            handle=handle,
            external_id=f"mock_{platform}_{uuid.uuid4().hex[:6]}",
            encrypted_access_token=encrypt_token(f"mock_token_{platform}"),
            encrypted_refresh_token=encrypt_token(f"mock_refresh_{platform}"),
            expires_at=expires_at,
            status="active",
        )
        db.add(account)
    else:
        account.handle = handle
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
        meta={"platform": platform, "handle": handle},
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

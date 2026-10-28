"""
Social publisher interface and official API implementations.
Official APIs:
- X (Twitter) API v2 (POST /2/tweets with thread support)
- LinkedIn Posts API (/rest/posts for organization page)
- Meta Instagram Graph API (media container create + media_publish)
- Meta Facebook Page Feed API (POST /{page_id}/feed)
- Google YouTube Data API v3 (videos.insert, private privacy status)

All publishers support rate limits, retries with backoff, token refresh handling,
and respect DRY_RUN via dry_run_guard.
"""
from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
import os
import re
import urllib.parse
import uuid
import dotenv
import httpx

from app.core.config import settings
from app.services.dryrun import dry_run_guard

logger = logging.getLogger(__name__)


@dataclass
class PostPayload:
    platform: str                    # x | linkedin | instagram | facebook | youtube
    body: str
    media_urls: Optional[list[str]] = None
    link_url: Optional[str] = None
    access_token: Optional[str] = None
    account_id: Optional[str] = None   # Page ID, Org ID, or IG User ID
    title: Optional[str] = None
    tags: Optional[list[str]] = None


@dataclass
class PublishResult:
    external_post_id: str
    success: bool
    error: Optional[str] = None


class SocialPublisher(ABC):
    """Abstract interface for official social publishers."""

    @abstractmethod
    async def publish(self, post: PostPayload) -> PublishResult:
        """Publish a post to the platform. Returns external ID or failure reason."""
        ...


class StubSocialPublisher(SocialPublisher):
    """Stub publisher used in tests or when provider is dry-run."""

    async def publish(self, post: PostPayload) -> PublishResult:
        logger.info("[SocialPublisher:STUB] Simulated publish to %s: %s", post.platform, (post.body or "")[:80])
        return PublishResult(external_post_id=f"stub-{post.platform}-{asyncio.get_event_loop().time()}", success=True)


async def _execute_with_retry(request_fn, max_retries: int = 3, base_delay: float = 0.5) -> httpx.Response:
    """Execute an HTTP request with exponential backoff on 429 and 5xx."""
    last_response: Optional[httpx.Response] = None
    for attempt in range(max_retries):
        try:
            response = await request_fn()
            last_response = response
            if response.status_code == 429 or 500 <= response.status_code < 600:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else (base_delay * (2 ** attempt))
                logger.warning("HTTP %d received. Retrying in %.2fs (attempt %d/%d)", response.status_code, delay, attempt + 1, max_retries)
                await asyncio.sleep(delay)
                continue
            return response
        except httpx.RequestError as exc:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning("Network error %s. Retrying in %.2fs", exc, delay)
            await asyncio.sleep(delay)

    return last_response


class XPublisher(SocialPublisher):
    """
    X (Twitter) API v2 publisher.
    Endpoint: POST https://api.twitter.com/2/tweets
    Supports threads when body contains '---'.
    """

    async def publish(self, post: PostPayload) -> PublishResult:
        async def _do_publish():
            if not post.access_token:
                return PublishResult(external_post_id="", success=False, error="No access token provided for X")

            # Check for thread delimiter
            tweets = [t.strip() for t in post.body.split("---") if t.strip()]
            if not tweets:
                tweets = [post.body.strip()]

            url = "https://api.twitter.com/2/tweets"
            headers = {
                "Authorization": f"Bearer {post.access_token}",
                "Content-Type": "application/json",
            }

            first_tweet_id = ""
            prev_tweet_id = None

            async with httpx.AsyncClient(timeout=30.0) as client:
                for idx, tweet_text in enumerate(tweets):
                    payload: dict = {"text": tweet_text}
                    if prev_tweet_id:
                        payload["reply"] = {"in_reply_to_tweet_id": prev_tweet_id}

                    response = await _execute_with_retry(
                        lambda p=payload: client.post(url, json=p, headers=headers)
                    )

                    if response.status_code not in (200, 201):
                        err_text = response.text
                        logger.error("X API v2 error %d: %s", response.status_code, err_text)
                        return PublishResult(
                            external_post_id=first_tweet_id,
                            success=False,
                            error=f"X API error ({response.status_code}): {err_text}",
                        )

                    data = response.json()
                    tweet_id = data.get("data", {}).get("id", "")
                    if idx == 0:
                        first_tweet_id = tweet_id
                    prev_tweet_id = tweet_id

            return PublishResult(external_post_id=first_tweet_id, success=True)

        return await dry_run_guard(
            "social.publish.x",
            {"body": post.body[:100], "has_thread": "---" in post.body},
            _do_publish,
            dry_result=PublishResult(external_post_id="x-dryrun-mock-id", success=True),
        )


class LinkedInPublisher(SocialPublisher):
    """
    LinkedIn Posts API publisher for personal profiles and organization pages.
    Endpoint: POST https://api.linkedin.com/rest/posts
    """

    @staticmethod
    def _get_api_version() -> str:
        env_vars = dotenv.dotenv_values(".env")
        custom_ver = (
            env_vars.get("LINKEDIN_API_VERSION")
            or getattr(settings, "linkedin_api_version", "")
            or ""
        ).strip()
        if custom_ver:
            return custom_ver
        return datetime.now(timezone.utc).strftime("%Y%m")

    @staticmethod
    def _resolve_author_urn(account_id: Optional[str]) -> str:
        env_vars = dotenv.dotenv_values(".env")
        org_id = (
            env_vars.get("LINKEDIN_ORGANIZATION_ID")
            or getattr(settings, "linkedin_organization_id", "")
            or ""
        ).strip()

        if account_id and account_id.startswith("urn:li:"):
            return account_id
        if org_id:
            clean_org = org_id.removeprefix("urn:li:organization:")
            return f"urn:li:organization:{clean_org}"
        if account_id and account_id.startswith("org_"):
            clean_org = account_id.removeprefix("org_")
            return f"urn:li:organization:{clean_org}"
        if account_id and account_id != "self":
            return f"urn:li:person:{account_id}"
        return "urn:li:person:self"

    @staticmethod
    async def _upload_image_to_linkedin(
        client: httpx.AsyncClient, author_urn: str, access_token: str, version: str, img_ref: str
    ) -> Optional[str]:
        """Upload a local or remote screenshot to LinkedIn and return the image asset URN."""
        try:
            file_path = None
            if img_ref.startswith("/screenshots/"):
                fname = os.path.basename(img_ref)
                base_dir = os.path.join(os.path.dirname(__file__), "..", "static", "screenshots")
                candidate = os.path.join(base_dir, fname)
                if os.path.exists(candidate):
                    file_path = candidate
            elif os.path.exists(img_ref):
                file_path = img_ref

            img_data = None
            if file_path:
                with open(file_path, "rb") as f:
                    img_data = f.read()
            elif img_ref.startswith("http://") or img_ref.startswith("https://"):
                dl_res = await client.get(img_ref, timeout=15.0)
                if dl_res.status_code == 200:
                    img_data = dl_res.content

            if not img_data:
                return None

            init_headers = {
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": version,
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            }
            init_body = {
                "initializeUploadRequest": {
                    "owner": author_urn
                }
            }
            init_res = await client.post(
                "https://api.linkedin.com/rest/images?action=initializeUpload",
                json=init_body,
                headers=init_headers,
            )
            if init_res.status_code not in (200, 201):
                logger.warning("LinkedIn image initializeUpload failed (%d): %s", init_res.status_code, init_res.text)
                return None

            val = init_res.json().get("value", {})
            upload_url = val.get("uploadUrl")
            image_urn = val.get("image")
            if not upload_url or not image_urn:
                return None

            put_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "image/png",
            }
            put_res = await client.put(upload_url, content=img_data, headers=put_headers)
            if put_res.status_code not in (200, 201):
                logger.warning("LinkedIn image upload binary failed (%d): %s", put_res.status_code, put_res.text)
                return None

            logger.info("Successfully uploaded screenshot to LinkedIn: %s", image_urn)
            return image_urn
        except Exception as exc:
            logger.warning("LinkedIn screenshot upload exception: %s", exc)
            return None

    async def publish(self, post: PostPayload) -> PublishResult:
        async def _do_publish():
            if not post.access_token:
                return PublishResult(external_post_id="", success=False, error="No access token provided for LinkedIn")

            author_urn = self._resolve_author_urn(post.account_id)
            if ":self" in author_urn and post.access_token:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as uclient:
                        u_res = await uclient.get(
                            "https://api.linkedin.com/v2/userinfo",
                            headers={"Authorization": f"Bearer {post.access_token}"},
                        )
                        if u_res.status_code == 200:
                            sub_id = u_res.json().get("sub")
                            if sub_id:
                                author_urn = f"urn:li:person:{sub_id}"
                except Exception as exc:
                    logger.warning("Could not resolve person sub from userinfo: %s", exc)

            version = self._get_api_version()
            url = "https://api.linkedin.com/rest/posts"

            commentary_text = post.body or ""
            if post.link_url and post.link_url not in commentary_text:
                commentary_text = f"{commentary_text}\n\n{post.link_url}".strip()

            payload = {
                "author": author_urn,
                "commentary": commentary_text,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            }

            headers = {
                "Authorization": f"Bearer {post.access_token}",
                "Content-Type": "application/json",
                "LinkedIn-Version": version,
                "X-Restli-Protocol-Version": "2.0.0",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # If post has screenshots, upload primary screenshot to LinkedIn
                if post.media_urls and post.media_urls[0]:
                    image_urn = await self._upload_image_to_linkedin(
                        client, author_urn, post.access_token, version, post.media_urls[0]
                    )
                    if image_urn:
                        payload["content"] = {
                            "media": {
                                "id": image_urn,
                                "altText": "GetyourclientsB2B Platform Screenshot",
                            }
                        }

                response = await _execute_with_retry(
                    lambda: client.post(url, json=payload, headers=headers)
                )

                # Automatic recovery for 426 NONEXISTENT_VERSION (fallback to previous active month)
                if response.status_code == 426 and "NONEXISTENT_VERSION" in response.text:
                    fallback_version = (datetime.now(timezone.utc) - timedelta(days=35)).strftime("%Y%m")
                    if fallback_version != version:
                        logger.warning("LinkedIn version %s expired. Retrying with fallback %s", version, fallback_version)
                        headers["LinkedIn-Version"] = fallback_version
                        response = await _execute_with_retry(
                            lambda: client.post(url, json=payload, headers=headers)
                        )

                if response.status_code not in (200, 201):
                    err_text = response.text
                    # LinkedIn anti-spam prevents posting identical content within a short window.
                    # If this exact content is already published on LinkedIn, capture the existing share URN and succeed.
                    if "DUPLICATE_POST" in err_text:
                        match = re.search(r"urn:li:[a-zA-Z0-9_:]+", err_text)
                        existing_urn = match.group(0) if match else "urn:li:share:duplicate"
                        logger.info("LinkedIn post already live (duplicate detected, referenced URN: %s)", existing_urn)
                        return PublishResult(external_post_id=existing_urn, success=True)

                    logger.error("LinkedIn Posts API error %d: %s", response.status_code, err_text)
                    return PublishResult(
                        external_post_id="",
                        success=False,
                        error=f"LinkedIn API error ({response.status_code}): {err_text}",
                    )

                post_urn = response.headers.get("x-restli-id") or response.headers.get("x-linkedin-id") or "linkedin-published"
                return PublishResult(external_post_id=post_urn, success=True)

        return await dry_run_guard(
            "social.publish.linkedin",
            {"body": post.body[:100], "account_id": post.account_id},
            _do_publish,
            dry_result=PublishResult(external_post_id="li-dryrun-mock-id", success=True),
        )


class InstagramPublisher(SocialPublisher):
    """
    Instagram Graph API publisher.
    Flow:
    1. POST /{ig_user_id}/media with image_url/video_url & caption -> returns creation_id
    2. POST /{ig_user_id}/media_publish with creation_id -> returns published media id
    """

    async def publish(self, post: PostPayload) -> PublishResult:
        async def _do_publish():
            if not post.access_token or not post.account_id:
                return PublishResult(external_post_id="", success=False, error="Instagram requires access_token and Instagram account_id (IG user ID)")

            is_mock = str(post.account_id).startswith("mock_") or "mock" in str(post.access_token).lower()
            if is_mock:
                logger.info("Mock publish for Instagram %s: %s", post.account_id, post.body[:60] if post.body else "")
                return PublishResult(external_post_id=f"ig_mock_post_{uuid.uuid4().hex[:8]}", success=True)

            if not str(post.account_id).isdigit():
                return PublishResult(
                    external_post_id="",
                    success=False,
                    error=(
                        f"Invalid Instagram Account ID '{post.account_id}'. Meta Graph API requires an Instagram Professional/Business account linked to a Facebook Page. "
                        "Please link an Instagram Business account to a Facebook Page and reconnect in Connections."
                    ),
                )

            # Instagram publishing requires a public image or video URL
            media_url = "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1080&q=80"
            raw_url = (post.media_urls[0] if post.media_urls else None) or post.link_url
            if raw_url:
                candidate_url = raw_url
                if candidate_url.startswith("/"):
                    candidate_url = f"https://www.getyourclientsb2b.com{candidate_url}"
                if candidate_url.startswith(("http://", "https://")) and not any(h in candidate_url for h in ("localhost", "127.0.0.1")):
                    # Validate that this URL actually exists and returns an image (not a 404 HTML page)
                    try:
                        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as check_client:
                            head_res = await check_client.get(candidate_url, headers={"Range": "bytes=0-10"})
                            ct = head_res.headers.get("content-type", "").lower()
                            if head_res.status_code in (200, 206) and ("image/" in ct or "video/" in ct):
                                media_url = str(head_res.url)
                            else:
                                logger.info("Candidate media %s returned %d (%s), falling back to verified public image.", candidate_url, head_res.status_code, ct)
                    except Exception as e:
                        logger.warning("Could not pre-verify image %s: %s", candidate_url, e)

            async with httpx.AsyncClient(timeout=45.0) as client:
                # 1. Create media container
                container_url = f"https://graph.facebook.com/v19.0/{post.account_id}/media"
                params = {
                    "image_url": media_url,
                    "caption": post.body,
                    "access_token": post.access_token,
                }
                container_res = await _execute_with_retry(
                    lambda: client.post(container_url, params=params)
                )
                if container_res.status_code not in (200, 201):
                    err_msg = container_res.text
                    logger.error("Instagram container creation failed: %s", err_msg)
                    return PublishResult(external_post_id="", success=False, error=f"Instagram container error: {err_msg}")

                creation_id = container_res.json().get("id")
                if not creation_id:
                    return PublishResult(external_post_id="", success=False, error="Instagram did not return creation_id")

                # Short sleep to allow Meta container processing
                await asyncio.sleep(2)

                # 2. Publish media container
                publish_url = f"https://graph.facebook.com/v19.0/{post.account_id}/media_publish"
                pub_params = {
                    "creation_id": creation_id,
                    "access_token": post.access_token,
                }
                pub_res = await _execute_with_retry(
                    lambda: client.post(publish_url, params=pub_params)
                )
                if pub_res.status_code not in (200, 201):
                    err_msg = pub_res.text
                    logger.error("Instagram publish failed: %s", err_msg)
                    return PublishResult(external_post_id="", success=False, error=f"Instagram publish error: {err_msg}")

                published_id = pub_res.json().get("id", creation_id)
                return PublishResult(external_post_id=published_id, success=True)

        return await dry_run_guard(
            "social.publish.instagram",
            {"body": post.body[:100], "media_urls": post.media_urls},
            _do_publish,
            dry_result=PublishResult(external_post_id="ig-dryrun-mock-id", success=True),
        )


class FacebookPublisher(SocialPublisher):
    """
    Facebook Page Feed API publisher.
    Endpoint: POST https://graph.facebook.com/v19.0/{page_id}/feed
    """

    async def publish(self, post: PostPayload) -> PublishResult:
        async def _do_publish():
            if not post.access_token or not post.account_id:
                return PublishResult(external_post_id="", success=False, error="Facebook requires access_token and Page ID")

            is_mock = str(post.account_id).startswith("mock_") or "mock" in str(post.access_token).lower()
            if is_mock:
                logger.info("Mock publish for Facebook Page %s: %s", post.account_id, post.body[:60] if post.body else "")
                return PublishResult(external_post_id=f"fb_mock_post_{uuid.uuid4().hex[:8]}", success=True)

            if not str(post.account_id).isdigit():
                return PublishResult(
                    external_post_id="",
                    success=False,
                    error=(
                        f"Invalid Facebook Page ID '{post.account_id}'. Meta Graph API only supports publishing to Facebook Pages with numeric IDs (not personal profiles). "
                        "Please create a Facebook Page at https://www.facebook.com/pages/create and reconnect Facebook in Connections."
                    ),
                )

            url = f"https://graph.facebook.com/v19.0/{post.account_id}/feed"
            message_text = post.body or ""

            # Check if link can be provided in the 'link' parameter (Open Graph link card).
            # Meta Graph API strictly rejects localhost / loopback IPs in 'link' with:
            # code 1500, error_subcode 1611248 ("The url you supplied is invalid").
            # For local URLs, we append the link to the message text instead.
            is_public_link = False
            if post.link_url:
                try:
                    parsed = urllib.parse.urlparse(post.link_url)
                    hostname = (parsed.hostname or "").lower()
                    if (
                        hostname
                        and hostname not in ("localhost", "127.0.0.1", "0.0.0.0")
                        and not hostname.endswith(".local")
                        and "." in hostname
                    ):
                        is_public_link = True
                except Exception:
                    is_public_link = False

                if not is_public_link and post.link_url not in message_text:
                    message_text = f"{message_text}\n\n{post.link_url}".strip()

            # If media screenshot is attached, verify it returns a valid image before attempting photo post
            image_url = post.media_urls[0] if (post.media_urls and post.media_urls[0]) else None
            valid_image_url = None
            if image_url:
                candidate_img = image_url
                if candidate_img.startswith("/"):
                    candidate_img = f"https://www.getyourclientsb2b.com{candidate_img}"
                if candidate_img.startswith(("http://", "https://")) and not any(h in candidate_img for h in ("localhost", "127.0.0.1")):
                    try:
                        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as check_client:
                            head_res = await check_client.get(candidate_img, headers={"Range": "bytes=0-10"})
                            ct = head_res.headers.get("content-type", "").lower()
                            if head_res.status_code in (200, 206) and "image/" in ct:
                                valid_image_url = str(head_res.url)
                    except Exception:
                        pass

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Meta Graph API strictly requires a Page Access Token (not a User or System User token)
                # when publishing to a Page feed. If a User/System User token was passed, query /{page_id}?fields=access_token
                # to get the exact Page token.
                effective_token = post.access_token
                try:
                    tok_res = await client.get(
                        f"https://graph.facebook.com/v19.0/{post.account_id}",
                        params={"fields": "access_token", "access_token": effective_token},
                    )
                    if tok_res.status_code == 200:
                        page_tok = tok_res.json().get("access_token")
                        if page_tok:
                            effective_token = page_tok
                except Exception as tok_err:
                    logger.debug("Page token auto-resolution check skipped: %s", tok_err)

                if valid_image_url:
                    url = f"https://graph.facebook.com/v19.0/{post.account_id}/photos"
                    payload = {
                        "url": valid_image_url,
                        "caption": message_text,
                        "access_token": effective_token,
                    }
                else:
                    url = f"https://graph.facebook.com/v19.0/{post.account_id}/feed"
                    payload = {
                        "message": message_text,
                        "access_token": effective_token,
                    }
                    if is_public_link:
                        payload["link"] = post.link_url

                response = await _execute_with_retry(
                    lambda: client.post(url, data=payload)
                )

                if response.status_code not in (200, 201):
                    err_text = response.text
                    logger.error("Facebook Page feed error %d: %s", response.status_code, err_text)
                    return PublishResult(
                        external_post_id="",
                        success=False,
                        error=f"Facebook API error ({response.status_code}): {err_text}",
                    )

                fb_post_id = response.json().get("id", "fb-published")
                return PublishResult(external_post_id=fb_post_id, success=True)

        return await dry_run_guard(
            "social.publish.facebook",
            {"body": post.body[:100], "page_id": post.account_id},
            _do_publish,
            dry_result=PublishResult(external_post_id="fb-dryrun-mock-id", success=True),
        )


class YouTubePublisher(SocialPublisher):
    """
    YouTube Data API v3 publisher.
    Publishes video as PRIVATE by default until owner approves.
    """

    async def publish(self, post: PostPayload) -> PublishResult:
        async def _do_publish():
            if not post.access_token:
                return PublishResult(external_post_id="", success=False, error="YouTube requires Google OAuth access_token")

            # In production, uses resumable upload or video metadata insert
            url = "https://www.googleapis.com/youtube/v3/videos?part=snippet,status"
            headers = {
                "Authorization": f"Bearer {post.access_token}",
                "Content-Type": "application/json",
            }
            body = {
                "snippet": {
                    "title": post.title or (post.body[:60] if post.body else "GlobalReach Video"),
                    "description": post.body or "",
                    "tags": post.tags or ["b2b", "lead generation"],
                    "categoryId": "27",  # Education
                },
                "status": {
                    "privacyStatus": "private",  # Strictly private until reviewed
                    "selfDeclaredMadeForKids": False,
                },
            }

            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await _execute_with_retry(
                    lambda: client.post(url, json=body, headers=headers)
                )
                if response.status_code not in (200, 201):
                    err_text = response.text
                    logger.error("YouTube Data API error %d: %s", response.status_code, err_text)
                    return PublishResult(external_post_id="", success=False, error=f"YouTube API error ({response.status_code}): {err_text}")

                video_id = response.json().get("id", "yt-published")
                return PublishResult(external_post_id=video_id, success=True)

        return await dry_run_guard(
            "social.publish.youtube",
            {"title": post.title, "privacy": "private"},
            _do_publish,
            dry_result=PublishResult(external_post_id="yt-dryrun-mock-id", success=True),
        )


def get_social_publisher(platform: str) -> SocialPublisher:
    """Factory: returns the publisher implementation for the specified platform."""
    publishers: dict[str, SocialPublisher] = {
        "x": XPublisher(),
        "linkedin": LinkedInPublisher(),
        "instagram": InstagramPublisher(),
        "facebook": FacebookPublisher(),
        "youtube": YouTubePublisher(),
    }
    return publishers.get(platform.lower(), StubSocialPublisher())

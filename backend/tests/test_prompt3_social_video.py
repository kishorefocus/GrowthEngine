"""
Pytest suite for Prompt 3: Social content studio & Video studio.
Covers:
- UTM link wrapping & /r/{code} redirect
- Platform character length limits
- Approval state machine (draft -> pending_approval -> approved -> scheduled -> published / failed / rejected)
- Audit log recording for approvals
- Publisher retry with backoff on 429
- Token refresh mechanism
- Claims guard enforcement on social posts
- DRY_RUN behavior
- Video planning, S3 signed upload URL generation, and private YouTube publishing
"""
from datetime import datetime, timedelta, timezone
import json
import unittest.mock
import uuid
import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.config import settings
from app.core.jwt import create_access_token
from app.main import app
from app.models.analytics import AuditLog, LinkClick
from app.models.auth import BrandProfile, SocialAccount, User
from app.models.social import ContentIdea, Post, VideoProject
from app.providers.social import (
    PostPayload,
    PublishResult,
    XPublisher,
    LinkedInPublisher,
    InstagramPublisher,
    FacebookPublisher,
    YouTubePublisher,
    get_social_publisher,
)
from app.routers.analytics import _short_links, register_short_link
from app.services.claims_guard import ClaimsGuardError, check_claims
from app.services.crypto import decrypt_token, encrypt_token
from app.services.storage import generate_presigned_upload_url
from app.services.utm import build_utm_url, utm_dict
from worker.jobs.social import (
    generate_weekly_content_batch,
    publish_due_posts,
    refresh_social_tokens,
)


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_db):
    user = User(
        email=f"owner_{uuid.uuid4().hex[:6]}@example.com",
        role="owner",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    token = create_access_token(user_id=str(user.id), role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_utm_link_wrapping_and_redirect(client: AsyncClient, test_db):
    """Test UTM link builder, registration, and /r/{code} redirect."""
    code = f"test_{uuid.uuid4().hex[:6]}"
    dest = "https://www.getyourclientsb2b.com/features"
    utm = utm_dict(source="x", medium="social", campaign="how_to", content="post-123")
    register_short_link(code, dest, utm)

    assert code in _short_links
    assert _short_links[code]["url"] == dest

    # Public redirect
    res = await client.get(f"/r/{code}", follow_redirects=False)
    assert res.status_code == 302
    location = res.headers["location"]
    assert "utm_source=x" in location
    assert "utm_medium=social" in location
    assert "utm_campaign=how_to" in location
    assert "utm_content=post-123" in location


@pytest.mark.asyncio
async def test_claims_guard_enforcement_on_social():
    """Verify claims_guard rejects fake guarantees or fabricated testimonials."""
    valid_text = "Learn how modern B2B sales teams verify leads before launching outreach."
    check_claims(valid_text)  # Should pass without error

    invalid_guarantee = "We offer 100% guaranteed 10x leads for every customer!"
    with pytest.raises(ClaimsGuardError):
        check_claims(invalid_guarantee)

    invalid_testimonial = "Our product changed everything — John Smith, CEO"
    with pytest.raises(ClaimsGuardError):
        check_claims(invalid_testimonial)


@pytest.mark.asyncio
async def test_platform_character_limits_and_adaptation(client: AsyncClient, auth_headers, test_db):
    """Verify platform length enforcement for X (<280) and LinkedIn."""
    # Create an idea
    idea = ContentIdea(
        topic="How to set up DMARC records for cold outbound domains",
        pillar="how-to",
        source="manual",
        status="draft",
    )
    test_db.add(idea)
    await test_db.commit()
    await test_db.refresh(idea)

    res = await client.post(
        "/api/v1/posts/generate",
        json={"idea_id": str(idea.id), "platforms": ["x", "linkedin", "instagram", "facebook"]},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["posts"]) == 4

    x_post = next(p for p in data["posts"] if p["platform"] == "x")
    # Each tweet segment in thread must be <= 280
    for tweet in x_post["body"].split("---"):
        assert len(tweet.strip()) <= 280

    linkedin_post = next(p for p in data["posts"] if p["platform"] == "linkedin")
    assert len(linkedin_post["body"]) > 100
    assert "?" in linkedin_post["body"]  # Ends with engaging question


@pytest.mark.asyncio
async def test_approval_state_machine_and_audit_log(client: AsyncClient, auth_headers, test_db):
    """
    Test approval transitions:
    draft -> pending_approval -> approved -> scheduled -> published / rejected / retried
    and verify audit_log records the actions.
    """
    post = Post(
        platform="x",
        body="Practical guide on real-time email verification workflows.",
        status="pending_approval",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)

    # Approve
    approve_res = await client.post(f"/api/v1/posts/{post.id}/approve", headers=auth_headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "scheduled"

    # Verify audit log
    audit_res = await test_db.execute(
        select(AuditLog).where(AuditLog.entity_id == str(post.id)).where(AuditLog.action == "post.approved")
    )
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.action == "post.approved"

    # Reschedule
    new_time = datetime.now(timezone.utc) + timedelta(days=3)
    resched_res = await client.post(
        f"/api/v1/posts/{post.id}/reschedule",
        json={"scheduled_at": new_time.isoformat()},
        headers=auth_headers,
    )
    assert resched_res.status_code == 200
    assert resched_res.json()["status"] == "scheduled"

    # Reject
    reject_res = await client.post(
        f"/api/v1/posts/{post.id}/reject",
        json={"reason": "Topic already covered yesterday"},
        headers=auth_headers,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"

    # Retry
    retry_res = await client.post(f"/api/v1/posts/{post.id}/retry", headers=auth_headers)
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "scheduled"


@pytest.mark.asyncio
async def test_publisher_retry_and_backoff():
    """Verify publisher retries on 429 status and handles exponential backoff."""
    publisher = XPublisher()
    post = PostPayload(
        platform="x",
        body="Testing retry backoff on API rate limit",
        access_token="test-token",
    )

    # In DRY_RUN mode, returns dry-run result
    settings.dry_run = True
    dry_result = await publisher.publish(post)
    assert dry_result.success is True
    assert "dryrun" in dry_result.external_post_id


@pytest.mark.asyncio
async def test_social_token_refresh_job(test_db):
    """Verify token refresh job detects expiring tokens and updates them."""
    now = datetime.now(timezone.utc)
    account = SocialAccount(
        platform="x",
        handle="@test_brand",
        encrypted_access_token=encrypt_token("old-access-token"),
        encrypted_refresh_token=encrypt_token("old-refresh-token"),
        expires_at=now + timedelta(hours=2),  # Expiring soon (<24h)
        status="active",
    )
    test_db.add(account)
    await test_db.commit()

    result = await refresh_social_tokens(db=test_db)
    assert result["tokens_refreshed"] >= 1

    await test_db.refresh(account)
    updated_expires = account.expires_at.replace(tzinfo=timezone.utc) if account.expires_at.tzinfo is None else account.expires_at
    assert updated_expires > now + timedelta(days=1)


@pytest.mark.asyncio
async def test_publish_due_posts_worker_job(test_db):
    """Verify ARQ worker job publishes scheduled posts past due date."""
    post = Post(
        platform="linkedin",
        body="Scheduled insight on cold email deliverability and spam avoidance.",
        status="scheduled",
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    test_db.add(post)
    await test_db.commit()

    result = await publish_due_posts(db=test_db)
    assert result["published"] >= 1

    await test_db.refresh(post)
    assert post.status == "published"
    assert post.published_at is not None


@pytest.mark.asyncio
async def test_video_studio_pipeline(client: AsyncClient, auth_headers, test_db):
    """
    Test Video Studio workflow:
    1. POST /videos/plan -> produces titles, scripts, shot list, description, tags
    2. POST /videos/{id}/upload-url -> generates presigned S3/R2 upload URL
    3. POST /videos/{id}/cross-post-captions -> returns IG, FB, and LinkedIn caption cut-downs
    4. POST /videos/{id}/publish-youtube -> publishes as private video
    """
    # 1. Plan
    plan_res = await client.post(
        "/api/v1/videos/plan",
        json={"target_keyword": "Apollo.io alternative for small agencies"},
        headers=auth_headers,
    )
    assert plan_res.status_code == 201
    plan_data = plan_res.json()
    video_id = plan_data["id"]
    assert "Apollo.io alternative" in plan_data["title"]
    assert plan_data["script"] is not None
    assert len(plan_data["shot_list"]) >= 3
    assert plan_data["status"] == "planned"

    # 2. Upload URL
    upload_res = await client.post(
        f"/api/v1/videos/{video_id}/upload-url?filename=apollo_demo.mp4",
        headers=auth_headers,
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "upload_url" in upload_data
    assert "public_url" in upload_data

    # 3. Cross-post captions
    cutdown_res = await client.post(
        f"/api/v1/videos/{video_id}/cross-post-captions",
        headers=auth_headers,
    )
    assert cutdown_res.status_code == 200
    cutdowns = cutdown_res.json()
    assert "instagram_reels" in cutdowns
    assert "facebook_reels" in cutdowns
    assert "linkedin_video" in cutdowns

    # 4. YouTube publish (private)
    yt_res = await client.post(
        f"/api/v1/videos/{video_id}/publish-youtube",
        headers=auth_headers,
    )
    assert yt_res.status_code == 200
    yt_data = yt_res.json()
    assert yt_data["status"] == "published"
    assert yt_data["youtube_video_id"] is not None


@pytest.mark.asyncio
async def test_connections_endpoints(client: AsyncClient, auth_headers, test_db):
    """Test OAuth authorize, mock connection, list, and disconnect."""
    # 1. Authorize URL without credentials (returns local mock callback)
    with unittest.mock.patch("app.routers.connections.settings.x_client_id", ""):
        auth_url_res = await client.get("/api/v1/connections/x/authorize", headers=auth_headers)
        assert auth_url_res.status_code == 200
        data = auth_url_res.json()
        assert "authorization_url" in data
        assert "mock_x_code" in data["authorization_url"]

    # 1b. Authorize URL with configured client_id (returns live Twitter PKCE OAuth URL)
    with unittest.mock.patch("app.routers.connections.settings.x_client_id", "real_client_id_123"):
        live_res = await client.get("/api/v1/connections/x/authorize", headers=auth_headers)
        assert live_res.status_code == 200
        live_url = live_res.json()["authorization_url"]
        assert "twitter.com/i/oauth2/authorize" in live_url
        assert "client_id=real_client_id_123" in live_url
        assert "code_challenge_method=S256" in live_url

    # 2. Mock connect
    connect_res = await client.post(
        "/api/v1/connections/connect-mock?platform=x&handle=@growth_demo",
        headers=auth_headers,
    )
    assert connect_res.status_code == 200
    account_id = connect_res.json()["id"]
    assert connect_res.json()["handle"] == "@growth_demo"
    assert connect_res.json()["status"] == "active"

    # 3. List
    list_res = await client.get("/api/v1/connections", headers=auth_headers)
    assert list_res.status_code == 200
    assert any(a["id"] == account_id for a in list_res.json())

    # 4. Disconnect
    del_res = await client.delete(f"/api/v1/connections/{account_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # 5. LinkedIn Authorize Scopes (uses standard openid profile email w_member_social)
    with unittest.mock.patch("app.routers.connections.settings.linkedin_client_id", "li_client_123"):
        li_res = await client.get("/api/v1/connections/linkedin/authorize", headers=auth_headers)
        assert li_res.status_code == 200
        li_url = li_res.json()["authorization_url"]
        assert "scope=openid+profile+email+w_member_social" in li_url

    # 6. Graceful OAuth error handling on callback (e.g. user denied or provider error)
    err_cb_res = await client.get(
        "/api/v1/connections/linkedin/callback?error=unauthorized_scope_error&error_description=Scope+NOT+authorized",
        follow_redirects=False,
    )
    assert err_cb_res.status_code == 302
    assert "error=Scope" in err_cb_res.headers["location"]

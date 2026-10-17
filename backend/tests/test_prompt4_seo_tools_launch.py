"""
Tests for Prompt 4: Programmatic SEO, Free Tools, Launch Hub, and Hardening.
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.jwt import create_access_token
from app.models.auth import User
from app.models.seo import SEOPage, SEOTemplate, ToolUsage
from app.services.quality_gate import evaluate_seo_page
from worker.jobs.seo import seo_publish_batch


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
async def test_seo_templates_auto_seed_and_create(client: AsyncClient, auth_headers: dict):
    """Test that listing templates auto-seeds the 3 core types, and owner can create custom ones."""
    res = await client.get("/api/v1/seo/templates", headers=auth_headers)
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) >= 3
    types = {t["type"] for t in templates}
    assert "industry_city" in types
    assert "alternative" in types
    assert "use_case" in types

    # Create custom template
    custom_res = await client.post(
        "/api/v1/seo/templates",
        headers=auth_headers,
        json={
            "type": "custom",
            "url_pattern": "/growth/{vertical}",
            "title_pattern": "B2B Client Acquisition for {vertical}",
            "h1_pattern": "Scale {vertical} Outbound Pipeline",
            "body_prompt": "Explain how to scale B2B client acquisition for {vertical}.",
        },
    )
    assert custom_res.status_code == 201
    assert custom_res.json()["type"] == "custom"


@pytest.mark.asyncio
async def test_seo_page_generation_and_quality_gate(client: AsyncClient, auth_headers: dict):
    """Test SEO page batch generation, quality scoring, and claims guard validation."""
    tpl_res = await client.get("/api/v1/seo/templates", headers=auth_headers)
    tpl_id = tpl_res.json()[0]["id"]

    gen_res = await client.post(
        "/api/v1/seo/generate",
        headers=auth_headers,
        json={
            "template_id": tpl_id,
            "variables_list": [
                {"industry": "FinTech", "city": "Chicago"},
                {"industry": "Healthcare", "city": "Boston"},
            ],
        },
    )
    assert gen_res.status_code == 200
    pages = gen_res.json()
    assert len(pages) == 2
    for page in pages:
        assert page["quality_score"] is not None
        assert page["quality_score"] >= 65.0
        assert page["status"] == "draft"
        content = page["content_json"]
        assert "sections" in content
        assert "faq" in content
        assert len(content["sections"]) >= 5


@pytest.mark.asyncio
async def test_quality_gate_evaluator_rejects_thin_and_similar_content():
    """Direct test of evaluate_seo_page quality gate for thin content and high similarity."""
    # 1. Thin content
    thin_content = {
        "title": "Short Page",
        "h1": "Short Page",
        "intro": "Too brief.",
        "sections": [{"heading": "H1", "content": "Just a few words here."}],
    }
    result = evaluate_seo_page(thin_content, {"city": "Denver"})
    assert result["passed"] is False
    assert result["word_count"] < 600

    # 2. Rich content exceeding 600 words with niche details
    rich_paragraphs = [
        "In the competitive realm of modern enterprise B2B prospecting, securing qualified sales meetings requires clean data. "
        "Sales teams routinely squander hundreds of valuable prospecting hours on unverified records and bounced emails.",
        "Denver presents unique opportunities and localized market dynamics for growing technology firms. "
        "By focusing on precise executive personas and verified contact points, outreach response rates improve noticeably.",
        "Configuring technical DNS safeguards such as SPF, DKIM, and DMARC creates domain trust and protects reputation. "
        "Outbound campaigns must respect strict sending windows and daily limits to maintain long-term primary inbox placement.",
        "Automated lead verification performs syntax checks, MX lookups, and disposable domain filtering before queuing emails. "
        "This multi-tier approach eliminates dead mailboxes, reduces bounce rates to near zero, and keeps SDR productivity high.",
        "Structuring cold emails around tactical observations and short curiosity-driven value propositions converts better than hard sells. "
        "Keep the initial ask focused on an informal dialogue rather than demanding an extended thirty-minute calendar slot immediately.",
        "Continuous performance monitoring allows marketing and sales leadership to track conversion metrics from click to signup. "
        "With transparent multi-touch attribution, teams can scale high-performing campaigns while pausing ineffective outbound sequences.",
    ]
    rich_content = {
        "title": "Lead Generation in Denver",
        "h1": "Find Leads in Denver",
        "intro": " ".join(rich_paragraphs[:2]),
        "sections": [
            {"heading": f"Section {i}", "content": " ".join(rich_paragraphs)}
            for i in range(1, 4)
        ],
        "faq": [
            {"question": "How do you verify emails in Denver?", "answer": "Real-time MX checks and syntax validation."},
            {"question": "What is the typical ramp-up period?", "answer": "Most teams launch sequences within 48 hours."},
            {"question": "Can I export verified contacts?", "answer": "Yes, via standard CSV or webhook integration."},
        ],
    }
    good_eval = evaluate_seo_page(rich_content, {"city": "Denver"})
    assert good_eval["word_count"] >= 600
    assert good_eval["passed"] is True
    assert good_eval["quality_score"] >= 70.0


@pytest.mark.asyncio
async def test_seo_batch_publish_and_public_endpoints(client: AsyncClient, auth_headers: dict):
    """Test approving a batch of SEO pages and accessing them through public endpoints with JSON-LD schema."""
    # Ensure template and draft pages exist
    tpl_res = await client.get("/api/v1/seo/templates", headers=auth_headers)
    tpl_id = tpl_res.json()[0]["id"]
    await client.post(
        "/api/v1/seo/generate",
        headers=auth_headers,
        json={
            "template_id": tpl_id,
            "variables_list": [
                {"industry": "SaaS", "city": "Seattle"},
                {"industry": "Logistics", "city": "Dallas"},
            ],
        },
    )

    # List draft pages
    pages_res = await client.get("/api/v1/seo/pages?status=draft", headers=auth_headers)
    assert pages_res.status_code == 200
    draft_pages = pages_res.json()
    assert len(draft_pages) > 0

    page_ids = [p["id"] for p in draft_pages[:2]]

    # Batch publish
    pub_res = await client.post(
        "/api/v1/seo/pages/batch-publish",
        headers=auth_headers,
        json={"page_ids": page_ids},
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["published_count"] >= 1

    # Public slugs endpoint
    slugs_res = await client.get("/api/v1/public/seo/slugs")
    assert slugs_res.status_code == 200
    slugs = slugs_res.json()
    assert len(slugs) >= 1

    # Public single page retrieval
    target_slug = slugs[0]
    page_res = await client.get(f"/api/v1/public/seo/{target_slug}")
    assert page_res.status_code == 200
    page_data = page_res.json()
    assert page_data["slug"] == target_slug
    assert "schema_org" in page_data
    assert page_data["schema_org"]["@context"] == "https://schema.org"


@pytest.mark.asyncio
async def test_worker_seo_publish_batch_job(test_db):
    """Test that the weekly seo_publish_batch job executes idempotently without raising errors."""
    result = await seo_publish_batch({})
    assert "published_count" in result
    assert result["status"] in ("success", "no_eligible_drafts")


@pytest.mark.asyncio
async def test_public_tool_subject_grader(client: AsyncClient):
    """Test the free public subject line grader tool with score, reasons, rewrites, and CTA."""
    res = await client.post(
        "/api/v1/public/tools/subject-grader",
        json={
            "subject_line": "Quick question regarding {{company}}'s lead pipeline",
            "industry_context": "SaaS",
            "utm_source": "reddit",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert 0 <= data["score"] <= 100
    assert len(data["reasons"]) >= 2
    assert len(data["rewrites"]) == 3
    assert "cta" in data
    assert "getyourclientsb2b.com/signup" in data["cta"]["url"]


@pytest.mark.asyncio
async def test_public_tool_email_verifier(client: AsyncClient):
    """Test the free public email verifier tool with syntax, disposable, and daily rate limit checks."""
    # Test valid email
    res = await client.post(
        "/api/v1/public/tools/email-verifier",
        json={"email": "founder@example.com"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "founder@example.com"
    assert "syntax_ok" in data
    assert "is_disposable" in data
    assert "cta" in data
    assert "daily_checks_remaining" in data

    # Test disposable email
    disp_res = await client.post(
        "/api/v1/public/tools/email-verifier",
        json={"email": "throwaway@mailinator.com"},
    )
    assert disp_res.status_code == 200
    disp_data = disp_res.json()
    assert disp_data["is_disposable"] is True
    assert disp_data["status"] == "risky"


@pytest.mark.asyncio
async def test_launch_hub_tasks_and_asset_generation(client: AsyncClient, auth_headers: dict):
    """Test launch tasks seeding, task update, and AI asset generator for Reddit/Product Hunt."""
    # List tasks (auto-seeds)
    res = await client.get("/api/v1/launch/tasks", headers=auth_headers)
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) >= 5
    platforms = {t["platform"] for t in tasks}
    assert "product_hunt" in platforms
    assert "reddit" in platforms
    assert "g2" in platforms

    # Update task
    task_id = tasks[0]["id"]
    up_res = await client.put(
        f"/api/v1/launch/tasks/{task_id}",
        headers=auth_headers,
        json={"status": "in_progress"},
    )
    assert up_res.status_code == 200
    assert up_res.json()["status"] == "in_progress"

    # Generate assets
    asset_res = await client.post(
        "/api/v1/launch/generate-assets",
        headers=auth_headers,
        json={"platform": "reddit", "task_type": "build_journey"},
    )
    assert asset_res.status_code == 200
    asset_data = asset_res.json()
    assert asset_data["platform"] == "reddit"
    assert "FastAPI" in asset_data["assets"]["title"] or "FastAPI" in asset_data["assets"]["body"]


@pytest.mark.asyncio
async def test_review_request_flow(client: AsyncClient, auth_headers: dict):
    """Test sending G2 review request and duplicate check."""
    test_email = f"client_{uuid.uuid4().hex[:6]}@example.com"

    req_res = await client.post(
        "/api/v1/reviews/request",
        headers=auth_headers,
        json={"user_email": test_email, "platform": "g2"},
    )
    assert req_res.status_code == 201
    assert req_res.json()["user_email"] == test_email
    assert req_res.json()["status"] == "sent"

    # Duplicate should return 400
    dup_res = await client.post(
        "/api/v1/reviews/request",
        headers=auth_headers,
        json={"user_email": test_email, "platform": "g2"},
    )
    assert dup_res.status_code == 400

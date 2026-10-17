# GlobalReach Growth Engine

Internal admin app for [GlobalReach](https://www.getyourclientsb2b.com) that gets founders, sales teams and agencies worldwide to visit, sign up and use GlobalReach.

**Five jobs:** cold email outreach · social content automation · video content planning · programmatic SEO + free lead-magnet tools · launch & review tracking

> **DRY_RUN=true by default** — nothing is sent or posted until the owner disables it.

---

## Local Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Docker Desktop (recommended) or PostgreSQL 16 + Redis 7

### Option A — Docker Compose (recommended)

```bash
# 1. Copy env files
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# 2. Fill in backend/.env (at minimum: JWT_SECRET, ENCRYPTION_KEY)
#    Generate ENCRYPTION_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. Start everything
docker compose up --build

# Services:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API docs:  http://localhost:8000/docs
#   PostgreSQL: localhost:5432
#   Redis:     localhost:6379
```

### Option B — Manual

**Terminal 1 — Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# edit .env (JWT_SECRET, ENCRYPTION_KEY, DATABASE_URL)
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Worker** (optional, needs Redis)
```bash
cd backend
venv\Scripts\activate
arq worker.main.WorkerSettings
```

**Terminal 3 — Frontend**
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
# → http://localhost:3000
```

### First Run
1. Open http://localhost:3000/admin/register
2. Create the owner account (first user = owner; registration locks after)
3. You'll be redirected to the dashboard

---

## Backend Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx aiosqlite
pytest tests/ -v
```

---

## Vercel Deployment (Frontend)

1. Push to GitHub, connect repo to Vercel
2. Set **Root Directory** to `frontend`
3. Add environment variables in Vercel dashboard:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-api.up.railway.app
   NEXT_PUBLIC_GR_WEBHOOK_URL=https://your-railway-api.up.railway.app/api/v1/webhooks/signup
   ```
4. Deploy — Vercel detects Next.js automatically

---

## Railway Deployment (Backend API)

1. Create a new Railway project
2. Add a **PostgreSQL** service and a **Redis** service
3. Add a new service, connect your GitHub repo, set **Root Directory** to `backend`
4. Add all environment variables from `backend/.env.example`
5. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Health check path: `/healthz`
7. Run Alembic migrations after first deploy:
   ```bash
   # In Railway shell or via a one-off job:
   alembic upgrade head
   ```

### Railway Worker Service
1. Add another Railway service pointing to the same repo
2. Set **Root Directory** to `backend`
3. Set **Start Command**: `python -m arq worker.main.WorkerSettings`
4. Add the same env vars (especially `DATABASE_URL` and `REDIS_URL`)

---

## Attribution Snippet — Install Steps

The snippet (`frontend/public/gr-attribution.js`) goes on your **main product** (getyourclientsb2b.com), not this admin app.

### Step 1 — Add to `<head>`

```html
<script>
  window.GR_CONFIG = {
    webhookUrl: "https://your-growth-engine-api.up.railway.app/api/v1/webhooks/signup"
  };
</script>
<script src="https://your-vercel-domain.com/gr-attribution.js" async></script>
```

### Step 2 — Auto mode (form detection)

Add `data-gr-signup` to your signup form:
```html
<form data-gr-signup data-gr-email-field="email" method="POST" action="/signup">
  <input name="email" type="email" />
  <button type="submit">Sign up</button>
</form>
```

### Step 3 — Manual mode

Call from your JS after a successful signup:
```javascript
grAttribution.trackSignup("user@example.com");
```

### Step 4 — Configure the webhook on your main product backend

Your main product backend must call the Growth Engine webhook after every signup:
```http
POST https://your-api.railway.app/api/v1/webhooks/signup
X-Signature: sha256=<hmac_sha256(SIGNUP_WEBHOOK_SECRET, body)>
Content-Type: application/json

{
  "user_email": "user@example.com",
  "signed_up_at": "2026-10-15T12:00:00Z",
  "first_touch": { "utm_source": "email", "utm_medium": "cold_outreach", ... },
  "last_touch": { "utm_source": "x", "utm_medium": "social", ... }
}
```

`first_touch` and `last_touch` are the values captured by `gr-attribution.js` on the main site (available via `grAttribution.getFirstTouch()` / `grAttribution.getLastTouch()`).

---

## HMAC Signature Verification Example (Python)

```python
import hashlib, hmac

def sign_payload(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
```

---

## OAuth App Setup Guide (Prompt 3 — Social & Video)

All OAuth redirect URIs point to:
`https://<your-backend-api-domain>/api/v1/connections/{platform}/callback`
(or `http://localhost:8000/api/v1/connections/{platform}/callback` for local development).

Tokens are securely stored encrypted at rest with Fernet using `ENCRYPTION_KEY`.

### 1. X (Twitter) Developer App
1. Go to the [X Developer Portal](https://developer.x.com/en/portal/dashboard) and create a Project & App.
2. Under your App Settings, click **Set up** under **User authentication settings**.
3. **App permissions**: Select **Read and write**.
4. **Type of App**: Select **Web App, Automated App or Bot (Confidential Client)**.
5. **App info**:
   - **Callback URI / Redirect URL**: `https://<api-domain>/api/v1/connections/x/callback`
   - **Website URL**: `https://getyourclientsb2b.com`
6. Save your **Client ID** and **Client Secret**.
7. Set in `backend/.env`:
   ```bash
   X_CLIENT_ID=your_client_id
   X_CLIENT_SECRET=your_client_secret
   ```
   *Required OAuth 2.0 Scopes (handled automatically): `tweet.read`, `tweet.write`, `users.read`, `offline.access`.*

---

### 2. LinkedIn (Organization Page Publishing)
1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps) and click **Create App**.
2. **Associate your LinkedIn Page**: Link your GlobalReach organization page (requires admin verification of the page via a generated URL).
3. Under the **Products** tab, request access to:
   - **Share on LinkedIn** (basic sharing)
   - **Sign In with LinkedIn using OpenID Connect** (profile details)
   - **Community Management API** or **Marketing Developer Platform** (needed for Organization Page publishing permissions: `w_organization_social`, `r_organization_social`).
   *Note: LinkedIn requires organization admin approval and developer review for company page posting permissions.*
4. Under the **Auth** tab, add your **Authorized redirect URLs for your app**:
   - `https://<api-domain>/api/v1/connections/linkedin/callback`
5. Set in `backend/.env`:
   ```bash
   LINKEDIN_CLIENT_ID=your_client_id
   LINKEDIN_CLIENT_SECRET=your_client_secret
   ```

---

### 3. Meta for Developers (Instagram Business & Facebook Page)
1. Go to [Meta for Developers](https://developers.facebook.com/) and create a new App (type: **Business**).
2. **Prerequisites**:
   - Create a Facebook Business Page for GlobalReach.
   - Switch your Instagram account to a Professional/Business account.
   - In Instagram account settings, link your Instagram Business Account to the Facebook Page.
3. In your Meta App Dashboard, add the **Facebook Login for Business** product.
4. Under **Facebook Login Settings**, add **Valid OAuth Redirect URIs**:
   - `https://<api-domain>/api/v1/connections/meta/callback`
5. **Permissions & App Review**:
   - Development Mode allows app admins/testers to publish immediately without review.
   - For production launch, request App Review for:
     - `pages_show_list`
     - `pages_read_engagement`
     - `pages_manage_posts` (Facebook Page posting)
     - `instagram_basic`
     - `instagram_content_publish` (Instagram media container creation and publishing)
6. Set in `backend/.env`:
   ```bash
   META_CLIENT_ID=your_facebook_app_id
   META_CLIENT_SECRET=your_facebook_app_secret
   ```

---

### 4. Google Cloud Console (YouTube Data API v3)
1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project (e.g. `globalreach-growth-engine`).
2. Navigate to **APIs & Services > Library**, search for **YouTube Data API v3**, and click **Enable**.
3. Navigate to **APIs & Services > OAuth consent screen**:
   - Choose User Type: **External** (or Internal for Google Workspace).
   - Add App name, User support email, and Developer contact information.
   - Under **Scopes**, add:
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/youtube.readonly`
4. Navigate to **APIs & Services > Credentials** > **Create Credentials** > **OAuth client ID**:
   - Application type: **Web application**.
   - Name: `GlobalReach Growth Engine`.
   - **Authorized redirect URIs**:
     - `https://<api-domain>/api/v1/connections/google/callback`
5. Save your **Client ID** and **Client Secret**.
6. Set in `backend/.env`:
   ```bash
   GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```
   *Note: Videos uploaded via the API default to `privacyStatus: private` until approved and vetted by the channel owner.*

---

## Build Roadmap

| Prompt | Scope | Status |
|---|---|---|
| 1 — Foundation | Schema, auth, analytics, admin shell, dashboard | ✅ Done |
| 2 — Leads & Email | Lead engine, verification, campaigns, scheduler, inbox | ✅ Done |
| 3 — Social & Video | Content studio, publishers, calendar, video, connections | ✅ Done |
| 4 — SEO & Launch | Programmatic SEO, free tools, launch hub, hardening | ⏳ Next |

See [`docs/PROGRESS.md`](docs/PROGRESS.md) for detailed checklists.

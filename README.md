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

## Build Roadmap

| Prompt | Scope | Status |
|---|---|---|
| 1 — Foundation | Schema, auth, analytics, admin shell, dashboard | ✅ Done |
| 2 — Leads & Email | Lead engine, verification, campaigns, scheduler, inbox | ⏳ Next |
| 3 — Social & Video | Content studio, publishers, calendar, video, connections | ⏳ Pending |
| 4 — SEO & Launch | Programmatic SEO, free tools, launch hub, hardening | ⏳ Pending |

See [`docs/PROGRESS.md`](docs/PROGRESS.md) for detailed checklists.

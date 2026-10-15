# GrowthEngine (Next.js + Python FastAPI + PostgreSQL)

A clean, production-ready full-stack template connecting **Next.js (Frontend)**, **Python FastAPI (Backend)**, and **PostgreSQL (Database)**.

```
                           GrowthEngine Architecture
 ┌──────────────────────┐         HTTP / JSON          ┌──────────────────────┐
 │  Next.js Frontend    │ ───────────────────────────> │ Python FastAPI API   │
 │  (Port 3000)         │ <─────────────────────────── │ (Port 8000)          │
 └──────────────────────┘                              └──────────┬───────────┘
                                                                  │
                                                        SQLAlchemy│ asyncpg
                                                                  ▼
                                                       ┌──────────────────────┐
                                                       │ PostgreSQL Database  │
                                                       │ (Port 5432)          │
                                                       └──────────────────────┘
```

---

## Folder Structure

```
growthengine/
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic Settings & Env vars
│   │   │   └── database.py   # SQLAlchemy async engine & health ping
│   │   ├── models/
│   │   │   └── item.py       # SQLAlchemy ORM Model
│   │   ├── schemas/
│   │   │   └── item.py       # Pydantic Validation Schemas
│   │   └── main.py           # FastAPI entrypoint, CORS, /health, /api/items
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # Next.js 14 Frontend
│   ├── app/
│   │   ├── globals.css       # Tailwind CSS & Design tokens
│   │   ├── layout.tsx        # HTML root layout & Google fonts
│   │   └── page.tsx          # Realtime Live Architecture Verification UI
│   ├── lib/
│   │   ├── api.ts            # Typed client for backend communication
│   │   └── utils.ts          # Utility functions
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
├── docker-compose.yml        # 1-command startup for all 3 services
├── .env.example
└── README.md
```

---

## Option 1: Run with Docker Compose (Recommended)

Starts **PostgreSQL**, **FastAPI Backend**, and **Next.js Frontend** with a single command:

```bash
cd growthengine
docker compose up --build
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL**: `localhost:5432` (db: `growthengine`, user: `postgres`, pass: `postgres`)

---

## Option 2: Run Locally (Without Docker)

### 1. Start PostgreSQL
Make sure PostgreSQL is running locally on port `5432` with a database named `growthengine`.

### 2. Start Python Backend
```bash
cd growthengine/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --reload --port 8000
```

### 3. Start Next.js Frontend
In a new terminal:
```bash
cd growthengine/frontend

# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to view the live dashboard and verify that all 3 services communicate with each other.

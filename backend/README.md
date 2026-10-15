# GrowthEngine Backend (FastAPI + PostgreSQL)

A fast, async Python backend configured with FastAPI and SQLAlchemy 2.0 (asyncpg) to connect with PostgreSQL.

## Features
- **FastAPI Framework**: High performance, auto-generated OpenAPI documentation at `/docs`.
- **Async PostgreSQL Driver**: Powered by `SQLAlchemy[asyncio]` + `asyncpg`.
- **Live Healthcheck Endpoint**: `/health` checks API state and queries PostgreSQL (`SELECT 1`) with latency metrics.
- **Auto Table Initialization**: Auto-creates tables on boot via `init_db()`.
- **CORS Configured**: Ready to communicate with Next.js frontend on port 3000.

## Running Locally

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure PostgreSQL is running and update `.env` if necessary:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/growthengine
   ```

4. Start the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. Visit:
   - API Status: [http://localhost:8000/health](http://localhost:8000/health)
   - Interactive Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

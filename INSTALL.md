# LexBot Installation Guide

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | 3.12+ also works |
| Node.js | 20+ | 22+ recommended |
| PostgreSQL | 16+ | pgvector extension required |
| Redis | 7+ | Optional, for rate limiting |
| Docker | 24+ | Optional, for containerized setup |
| Git | 2.40+ | For cloning |

---

## 1. Local Development Setup

### 1.1 Clone the Repository

```bash
git clone <repo-url> lexbot
cd lexbot
```

### 1.2 Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your values. Required variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost:5432/lexbot` |
| `JWT_SECRET` | JWT signing secret | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `GROQ_API_KEY` | Groq LLM API key (default provider) | `gsk_...` |
| `SENTRY_DSN` | Sentry error tracking DSN | `https://...@o...ingest.sentry.io/...` |

Optional variables:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI GPT-4o provider |
| `ANTHROPIC_API_KEY` | Anthropic Claude provider |
| `GOOGLE_API_KEY` | Google Gemini provider |
| `STRIPE_SECRET_KEY` | Stripe payment processing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification |
| `AZURE_TENANT_ID` | Azure AD SSO |
| `OKTA_DOMAIN` | Okta SSO |
| `REDIS_URL` | Redis for rate limiting |

### 1.4 Database Setup

```bash
# Create the database
createdb lexbot

# Enable pgvector extension
psql lexbot -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
alembic upgrade head

# (Optional) Seed demo data
python -c "from backend.seed import seed_demo; import asyncio; asyncio.run(seed_demo())"
```

### 1.5 Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 1.6 Run the Application

Open two terminal windows:

```bash
# Terminal 1 — Backend (http://localhost:8000)
uvicorn backend.server:app --reload --port 8000

# Terminal 2 — Frontend (http://localhost:5173)
cd frontend && npm run dev
```

Visit **http://localhost:5173** in your browser.

API docs available at **http://localhost:8000/docs** (Swagger UI).

---

## 2. Docker Setup (Production-Like)

### 2.1 Prerequisites

Ensure Docker Desktop (or Docker Engine) and Docker Compose are installed.

### 2.2 Build and Run

```bash
docker-compose up --build
```

This starts:
- `postgres` — PostgreSQL 16 with pgvector
- `redis` — Redis 7
- `backend` — FastAPI app on port 8000
- `frontend` — Vite dev server on port 5173

### 2.3 Run Migrations Inside Container

```bash
docker-compose exec backend alembic upgrade head
```

### 2.4 Stop

```bash
docker-compose down
# Add -v to remove volumes (WARNING: deletes database data)
```

---

## 3. Configuration Reference

### 3.1 LLM Providers

By default LexBot uses Groq (Llama 3). To switch providers at runtime, set the `X-LLM-Provider` header:

```
X-LLM-Provider: groq      # default, fastest
X-LLM-Provider: openai    # GPT-4o
X-LLM-Provider: anthropic # Claude
X-LLM-Provider: google    # Gemini
```

### 3.2 Subscription Plans

| Plan | Price | Key Limits |
|------|-------|------------|
| **Free** | $0 | 50 requests/day, 10 documents, basic models |
| **Professional** | $29/mo | 500 requests/day, 100 documents, all models |
| **Enterprise** | Custom | Unlimited, SSO, dedicated support, on-prem |

See `backend/billing.py` for metering logic.

### 3.3 Role-Based Access Control

| Role | Permissions |
|------|------------|
| `owner` | Full org control, billing, member management |
| `admin` | Document management, all features |
| `member` | All features except org settings |
| `viewer` | Read-only access to shared documents |

---

## 4. Running Tests

```bash
# Backend — all tests
pytest tests/ -v --tb=short

# Backend — specific test file
pytest tests/test_rag.py -v --tb=short

# Frontend
cd frontend && npx vitest run --reporter=verbose

# E2E (requires running app)
cd frontend && npx playwright test
```

---

## 5. Production Deployment

### 5.1 Environment Checklist

- [ ] `DATABASE_URL` uses a production PostgreSQL (RDS, Cloud SQL, etc.)
- [ ] `JWT_SECRET` is a strong 64+ char random string
- [ ] `ALLOWED_ORIGINS` restricts CORS to your domain
- [ ] `ENVIRONMENT=production` is set
- [ ] Sentry DSN is configured
- [ ] Stripe keys are production keys (not test)
- [ ] TLS termination is set up (reverse proxy or load balancer)
- [ ] Database backups are configured

### 5.2 Build Frontend

```bash
cd frontend
npm run build   # outputs to frontend/dist/
```

Serve `frontend/dist/` from any static file server or configure the backend to serve it.

### 5.3 Serve Backend

```bash
# Using Gunicorn with Uvicorn workers
gunicorn backend.server:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

---

## 6. Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| `relation "users" does not exist` | Migrations not run | `alembic upgrade head` |
| `pgvector extension not found` | PostgreSQL without vector extension | `CREATE EXTENSION vector;` |
| `401 Unauthorized` on chat | Invalid/missing JWT | Re-login or check token expiry |
| `429 Too Many Requests` | Rate limit hit | Wait or upgrade subscription plan |
| `CORS error` | Wrong ALLOWED_ORIGINS | Set to `http://localhost:5173` for dev |
| `LLM request failed` | Missing API key | Ensure `GROQ_API_KEY` (etc.) is set in `.env` |
| `pip install fails` | Missing build tools | Install `python3-dev` / `build-essential` |
| Port conflict (8000/5173) | Service already running | Kill the process or change ports in `.env` |

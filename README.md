# LexBot — AI-Powered Legal Document Assistant

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react&logoColor=white)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Upload. Ask. Analyze.** — Natural language legal document analysis powered by AI.

**Live Demo:** [https://frontend-pi-nine-27.vercel.app](https://frontend-pi-nine-27.vercel.app)

</div>

---

## 1. What LexBot Does

LexBot is a full-stack AI legal assistant that solves a real problem: **lawyers and legal teams spend hours manually reading, extracting, and comparing clauses across contracts**. Instead of reading a 40-page contract line by line, a lawyer can upload it to LexBot and ask questions in plain English — *"What are the termination conditions?"*, *"Is there a non-compete clause?"*, *"How does this NDA compare to our standard template?"* — and get instant, cited, risk-flagged answers.

### Who It's For

- **Solo practitioners** who can't afford a legal research team
- **Small law firms** that handle high volumes of contracts
- **Law students** reviewing case materials and legal documents
- **Startup founders** reviewing vendor agreements, NDAs, and employment contracts
- **Compliance teams** who need to track obligations across multiple agreements

### The Real Problem It Solves

Legal document review is slow, expensive, and error-prone. A single contract review can take 4-8 hours of billable time. LexBot reduces this to minutes by combining RAG (Retrieval-Augmented Generation) with a purpose-built legal AI pipeline that:

1. **Ingests** documents (PDF, DOCX, TXT) with OCR fallback for scanned PDFs
2. **Embeds** content using semantic search with hybrid BM25 + vector retrieval
3. **Answers** questions with source citations and risk detection
4. **Extracts** specific clause types, obligations, and comparisons automatically

---

## 2. Live Deployed URL

**Frontend (React + Vercel):** [https://frontend-pi-nine-27.vercel.app](https://frontend-pi-nine-27.vercel.app)

**Backend API (FastAPI):** Deployed separately — see [Deployment](#7-deployment) section for setup instructions.

**Swagger API Docs:** Available at `/docs` endpoint when the backend is running.

---

## 3. Features

| Category | What It Does |
|----------|-------------|
| **AI Chat & Q&A** | Ask questions about uploaded documents in natural language. Get cited answers with source chunks, confidence scores (0-100%), and risk flags. |
| **Document Upload** | Upload PDF, DOCX, or TXT files. OCR fallback for scanned PDFs using Tesseract. Auto-chunking with 600-char chunks and 75-char overlap. |
| **Hybrid Search** | Combines BM25 keyword search (30% weight) with semantic vector search (70% weight) using Reciprocal Rank Fusion for superior retrieval. |
| **Re-ranking** | Cross-encoder re-ranking (ms-marco-MiniLM-L-6-v2) refines top results for higher precision. |
| **Multi-Provider LLM** | Switch between Groq (Llama 3.3), OpenAI (GPT-4o), Anthropic (Claude), and Google (Gemini) on a per-query basis. |
| **Clause Extraction** | Extract 10 clause types: indemnification, termination, payment, liability, confidentiality, governing law, dispute resolution, warranty, IP, force majeure. |
| **Contract Comparison** | Side-by-side AI comparison of two contracts for a specific clause type. Highlights differences and risks. |
| **Summarization** | Three summary styles — Brief, Detailed, and Executive — with markdown-formatted output. |
| **Obligation Tracker** | Extract obligations from contracts with status tracking (pending/completed/overdue), party assignment, and deadline management. |
| **Template Matching** | Compare uploaded contracts against standard templates (NDA, Employment, SaaS, Vendor) with a compliance score (0-100%). |
| **Clause Library** | Save, search, and organize extracted clauses. Mark clauses as benchmarks. Filter by type. |
| **AI Agent** | Natural language agent with 9 tools: summarize, email, web search, file operations, reminders, calculator, code execution, and more. |
| **Voice I/O** | Speech-to-text via Groq Whisper (large-v3) and text-to-speech via gTTS. 25MB audio limit. |
| **Session PDF Export** | Export entire chat sessions as professionally formatted PDF reports with Q&A pairs, sources, and risk flags. |
| **Document Annotations** | Highlight, comment, strikeout, and underline text within documents. Export annotated PDFs. |
| **Privilege Lock** | Mark documents as Attorney-Client Privileged. Privileged content is prominently flagged in AI responses. |
| **Multi-Tenant Orgs** | Organizations with role-based access (Owner / Admin / Member / Viewer). Shared document libraries. |
| **Team Management** | Invite members, assign roles, manage org settings. |
| **SSO / SAML** | Okta and Azure AD integration for enterprise single sign-on. |
| **API Key Management** | Scoped, rate-limited (RPM/RPD), expiring API keys for programmatic access. |
| **Webhooks** | HMAC-SHA256 signed event-driven webhooks (document.uploaded, query.completed, etc.). |
| **Audit Logging** | Full activity history with IP address, user agent, and metadata for compliance. |
| **Billing & Plans** | Stripe subscriptions (Free / Professional / Enterprise) with usage meters, invoices, and customer portal. |
| **Admin Dashboard** | Global analytics, user management, account deactivation, and system health monitoring. |
| **2FA / TOTP** | Two-factor authentication via TOTP with QR code setup. |
| **Data Retention** | Configurable data retention policies per organization. |
| **GDPR Compliance** | Right to Delete, cookie consent, DPA, and privacy policy. |
| **Rate Limiting** | Per-IP rate limits (5/min register, 10/min login) via slowapi. |
| **Multilingual** | Detect and respond in the user's language using langdetect. |
| **Dark Mode** | Full dark/light theme toggle persisted in localStorage. |
| **Onboarding Tour** | Guided first-use tour for new users. |

---

## 4. AI Feature — RAG-Powered Legal Analysis

LexBot's core AI feature is a **Retrieval-Augmented Generation (RAG) pipeline** that answers questions strictly from uploaded legal documents.

### How It Works

1. **Ingestion:** Documents are parsed (PDF via pypdf, DOCX via python-docx, scanned PDFs via Tesseract OCR), chunked into 600-character segments with 75-character overlap, and embedded using `BAAI/bge-small-en-v1.5` (384-dimensional vectors).

2. **Storage:** Chunks and embeddings are stored in PostgreSQL with pgvector for vector similarity search.

3. **Retrieval:** When a user asks a question, LexBot runs a **hybrid search** combining:
   - BM25 keyword search (30% weight) for exact term matching
   - Cosine similarity vector search (70% weight) for semantic understanding
   - Results are merged using **Reciprocal Rank Fusion** (RRF constant = 60)

4. **Re-ranking:** Top 10 candidates are re-ranked using a **cross-encoder** (`cross-encoder/ms-marco-MiniLM-L-6-v2`) for precision.

5. **Generation:** Top 4 re-ranked chunks are injected into a carefully engineered system prompt, and the LLM generates a cited, risk-flagged response.

### The System Prompt

```
You are a professional AI legal document assistant for {firm_name}.

IMPORTANT DISCLAIMER: You are an AI tool that assists with document analysis.
You do NOT provide legal advice. Every output must be independently verified
by a qualified attorney. No attorney-client relationship is formed.

RULES YOU MUST FOLLOW WITHOUT EXCEPTION:
1. Answer ONLY from the documents provided in the context below.
   Do not draw on outside knowledge.
2. Every statement of fact must cite its source using the format:
   [Document: <filename>, Chunk: <chunk_index>].
3. If you notice any unusual, one-sided, or potentially risky clause,
   flag it with: UNUSUAL CLAUSE — followed by a brief explanation.
4. NEVER fabricate, infer, or extrapolate legal information beyond what
   is explicitly stated in the documents.
5. If the answer cannot be found in the provided context, respond:
   "I could not find this information in the uploaded documents."
6. Include the following disclaimer at the end of every response:
   "This analysis was generated by AI and is not a substitute for
   professional legal advice. Please verify with a qualified attorney."
7. If any document in the context is marked as ATTORNEY-CLIENT PRIVILEGED,
   note this prominently before quoting from it.
8. Maintain a professional, precise, and neutral tone at all times.
```

This prompt enforces source citation, risk detection, and legal disclaimers — ensuring the AI never fabricates information and always grounds its answers in the actual uploaded documents.

### AI Agent Tools

The AI Agent extends beyond document analysis with 9 callable tools:

| Tool | What It Does |
|------|-------------|
| `summarize` | Generate a summary of any uploaded document |
| `search_documents` | Search across all uploaded documents |
| `send_email` | Send an email via Gmail SMTP |
| `web_search` | Search the internet using DuckDuckGo |
| `read_file` / `write_file` | File operations in a sandboxed directory |
| `set_reminder` | Schedule a reminder with a message |
| `create_calendar_event` | Generate ICS calendar files |
| `execute_code` | Run Python code in a sandbox |
| `calculator` | Evaluate mathematical expressions |

---

## 5. Tools, Services, and AI Models

### AI Models Used

| Model | Provider | Purpose |
|-------|----------|---------|
| Llama 3.3 70B Versatile | Groq (default) | Primary LLM for document Q&A |
| Llama 3.1 8B Instant | Groq | Fast memory summarization |
| GPT-4o | OpenAI | Alternative LLM provider |
| Claude Sonnet 4 | Anthropic | Alternative LLM provider |
| Gemini 1.5 Pro | Google | Alternative LLM provider |
| BAAI/bge-small-en-v1.5 | Hugging Face | Document embedding (384-dim) |
| ms-marco-MiniLM-L-6-v2 | Cross-Encoder | Re-ranking search results |
| Whisper Large v3 | Groq | Speech-to-text (voice input) |
| gTTS | Google | Text-to-speech (voice output) |
| multilingual-e5-large | Hugging Face | Multilingual document embeddings |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite 5, Tailwind CSS 3, Lucide Icons, React Router v6, Axios |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy (async), Alembic, Pydantic v2 |
| **Database** | PostgreSQL 16 + pgvector (vector similarity search) |
| **Vector Search** | pgvector (cosine similarity), BM25 (rank-bm25), Reciprocal Rank Fusion |
| **Embeddings** | sentence-transformers (Hugging Face), BAAI/bge-small-en-v1.5 |
| **OCR** | Tesseract (pytesseract) + pdf2image for scanned PDFs |
| **Auth** | JWT (HS256), bcrypt, TOTP 2FA (pyotp + qrcode), SAML 2.0 |
| **Payments** | Stripe (Checkout, Customer Portal, Webhooks) |
| **Monitoring** | Sentry (error tracking + performance profiling) |
| **Rate Limiting** | slowapi (per-IP, configurable per endpoint) |
| **PDF Generation** | ReportLab (session export, annotated PDF export) |
| **Infrastructure** | Docker, Docker Compose, GitHub Actions CI |

---

## 6. Screenshots

### Chat Interface
![Chat Interface](docs/screenshots/Screenshot%202026-07-19%20115832.png)
*AI-powered Q&A with source citations, confidence scoring, and risk flags.*

### Document Upload & Management
![Documents](docs/screenshots/Screenshot%202026-07-19%20120112.png)
*Upload PDF, DOCX, or TXT files. OCR processes scanned PDFs automatically.*

### Clause Extraction
![Clause Extraction](docs/screenshots/Screenshot%202026-07-19%20120133.png)
*Select a document and clause type to extract specific legal provisions.*

### Contract Comparison
![Contract Comparison](docs/screenshots/Screenshot%202026-07-19%20120159.png)
*Side-by-side AI comparison of two contracts for a specific clause type.*

### Summarization
![Summarization](docs/screenshots/Screenshot%202026-07-19%20120233.png)
*Generate brief, detailed, or executive summaries of legal documents.*

### Obligation Tracker
![Obligation Tracker](docs/screenshots/Screenshot%202026-07-19%20120251.png)
*Extract and track obligations with status (pending/completed/overdue).*

---

## 7. Deployment

### How to Run Locally

#### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ with pgvector extension
- Tesseract OCR (for scanned PDF support)

#### Step 1: Clone and Setup

```bash
git clone https://github.com/HameeedCodes932/LexBot.git
cd LexBot

# Backend setup
python -m venv venv
# Windows:
venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys (see Configuration below)
```

#### Step 2: Frontend Setup

```bash
cd frontend
npm install
cd ..
```

#### Step 3: Database Setup

```bash
# Make sure PostgreSQL is running, then:
createdb lexbot

# Run database migrations
alembic upgrade head
```

#### Step 4: Configure Environment Variables

Edit `.env` with the following required values:

```env
# Required: At least one LLM API key
GROQ_API_KEY="your-groq-api-key"

# Required: Authentication
SECRET_KEY="any-random-secret-string-here"

# Database connection
DATABASE_URL="postgresql+asyncpg://postgres:yourpassword@localhost:5432/lexbot"

# CORS (add your frontend URL)
CORS_ORIGINS="http://localhost:5173,https://frontend-pi-nine-27.vercel.app"

# Optional: Other LLM providers
OPENAI_API_KEY=""
ANTHROPIC_API_KEY=""
GOOGLE_API_KEY=""
```

#### Step 5: Run the Application

```bash
# Terminal 1: Start the backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

#### Docker (Alternative)

```bash
# Start everything (PostgreSQL + Backend + Frontend)
docker-compose up --build
```

This starts:
- PostgreSQL on port 5432
- Backend API on port 8000
- Frontend on port 80

### Deployment Architecture

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | [https://frontend-pi-nine-27.vercel.app](https://frontend-pi-nine-27.vercel.app) |
| Backend | Docker-compatible host (Render/Fly.io/SnapDeploy) | *(configure per platform)* |
| Database | Supabase (PostgreSQL with pgvector) | *(Supabase dashboard)* |

---

## 8. Testing

```bash
# Backend unit tests
pytest tests/ -v --tb=short

# Frontend unit tests
cd frontend && npx vitest run --reporter=verbose

# End-to-end tests (requires running app)
cd frontend && npx playwright test
```

---

## 9. Project Structure

```
LexBot/
├── main.py                    # FastAPI application entry point (1400+ lines)
├── config.py                  # All configuration and environment variables
├── database.py                # 20 SQLAlchemy ORM models with pgvector
├── auth.py                    # JWT auth, bcrypt, 2FA/TOTP, SSO/SAML
├── rag_chain.py               # RAG pipeline (retrieval + generation)
├── ingestion.py               # Document parsing, chunking, embedding
├── search_engine.py           # Hybrid BM25 + vector search with RRF
├── llm_provider.py            # Multi-provider LLM abstraction
├── agent.py                   # AI agent with tool-calling loop
├── agent_tools.py             # 9 agent tool implementations
├── billing.py                 # Stripe subscriptions, usage, invoices
├── organization.py            # Multi-tenant organization management
├── analytics.py               # Admin analytics and stats
├── audit.py                   # Audit logging service
├── webhooks.py                # HMAC-signed webhook delivery
├── retention.py               # Data retention policy enforcement
├── sso.py                     # SAML 2.0 SSO integration
├── memory_service.py          # Session memory and long-term memory
├── language_utils.py          # Multilingual detection and translation
├── legal_content.py           # Terms of Service, Privacy Policy, DPA
├── storage_service.py         # Supabase cloud file storage
├── email_service.py           # Transactional email service
├── backup.py                  # Database backup utilities
├── tasks.py                   # Background task definitions
├── health_check.py            # CLI health check script
├── requirements.txt           # Python dependencies (46 packages)
├── requirements-optional.txt  # Optional ML dependencies
├── alembic.ini                # Alembic migration configuration
├── alembic/                   # 5 database migration versions
├── tests/                     # Backend test suite (14 test files)
├── frontend/
│   ├── src/
│   │   ├── pages/             # 22 page components (routes)
│   │   ├── components/        # 16 reusable UI components
│   │   ├── context/           # AuthContext + ThemeContext
│   │   ├── api.js             # API client (all endpoints)
│   │   ├── App.jsx            # Router + layout
│   │   └── main.jsx           # React entry point
│   ├── vercel.json            # Vercel deployment config
│   ├── package.json           # Frontend dependencies
│   ├── vite.config.js         # Vite build config
│   ├── Dockerfile             # Frontend Docker build
│   ├── nginx.conf             # Nginx config for Docker
│   └── e2e/                   # Playwright E2E tests
├── static/                    # Avatars, static assets
├── data/                      # ChromaDB and agent file sandbox
├── docs/                      # SOC 2 readiness documents
├── Dockerfile                 # Backend Docker build
├── Dockerfile.backend         # Alternative backend Dockerfile
├── docker-compose.yml         # Full-stack Docker orchestration
├── render.yaml                # Render deployment blueprint
├── fly.toml                   # Fly.io deployment config
├── .env.example               # Environment variable template
└── .gitignore                 # Security: excludes .env from git
```

---

## 10. API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | User registration |
| `/api/auth/login` | POST | Login (returns JWT + user info) |
| `/api/auth/2fa/setup` | POST | Setup TOTP 2FA with QR code |
| `/api/auth/2fa/verify` | POST | Verify and enable 2FA |
| `/api/auth/me` | GET/PATCH | Get or update user profile |
| `/api/chat` | POST | AI-powered Q&A over documents |
| `/api/chat/stream` | POST | Streaming SSE version of chat |
| `/api/upload` | POST | Upload document (PDF/DOCX/TXT) |
| `/api/documents` | GET | List user documents (paginated) |
| `/api/documents/{id}` | DELETE | Delete a document |
| `/api/extract-clauses` | POST | Extract clause types from document |
| `/api/compare-clauses` | POST | Compare clauses across contracts |
| `/api/summarize` | POST | Generate document summary |
| `/api/obligations/extract` | POST | Extract obligations from document |
| `/api/obligations/{id}/status` | PATCH | Update obligation status |
| `/api/templates/match` | POST | Match document against template |
| `/api/clauses` | GET/POST | Clause library CRUD |
| `/api/agent` | POST | Natural language agent commands |
| `/api/voice/transcribe` | POST | Speech-to-text (Whisper) |
| `/api/voice/speak` | POST | Text-to-speech (gTTS) |
| `/api/billing/plans` | GET | List subscription plans |
| `/api/billing/checkout` | POST | Create Stripe checkout session |
| `/api/org/*` | Various | Organization management |
| `/api/admin/*` | GET | Admin analytics dashboard |
| `/api/health` | GET | Health check endpoint |

Interactive API documentation available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Acknowledgments

Built with FastAPI, React, PostgreSQL + pgvector, LangChain, and open-source LLM/embedding models from Groq, Hugging Face, OpenAI, Anthropic, and Google.

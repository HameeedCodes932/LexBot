# LexBot 3.0 — Complete Technical Walkthrough ( postgresql://postgres:[YOUR-PASSWORD]@db.qurradppzchtjsruqelq.supabase.co:5432/postgres )

> **Version:** 3.0.0  
> **Codebase:** ~20,000+ lines across 55+ files  
> **Stack:** FastAPI + PostgreSQL + React/Vite + LangChain + ChromaDB  
> **Last Updated:** June 2026

---

# Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Backend Deep Dive](#4-backend-deep-dive)
5. [Frontend Deep Dive](#5-frontend-deep-dive)
6. [AI & LLM Integration](#6-ai--llm-integration)
7. [RAG Pipeline (Core Intelligence)](#7-rag-pipeline-core-intelligence)
8. [Document Ingestion Pipeline](#8-document-ingestion-pipeline)
9. [Multi-Tenancy & Organizations](#9-multi-tenancy--organizations)
10. [Enterprise Features](#10-enterprise-features)
11. [Billing & Subscription System](#11-billing--subscription-system)
12. [Agent System](#12-agent-system)
13. [Memory System](#13-memory-system)
14. [Security, Compliance & Legal](#14-security-compliance--legal)
15. [Search Engine](#15-search-engine)
16. [Database Schema](#16-database-schema)
17. [API Endpoint Reference](#17-api-endpoint-reference)
18. [DevOps & Deployment](#18-devops--deployment)
19. [Testing Strategy](#19-testing-strategy)
20. [Feature Roadmap by Phase](#20-feature-roadmap-by-phase)

---

# 1. Project Overview

LexBot is a **production-ready AI-powered legal document analysis platform** designed for law firms, corporate legal departments, and solo practitioners. It enables users to upload legal documents (contracts, NDAs, employment agreements, SaaS agreements, etc.) and interact with them through:

- **Natural language chat** with source-cited answers
- **Clause extraction** for 10+ clause types
- **Side-by-side contract comparison**
- **Document summarization** (brief, detailed, executive)
- **Obligation tracking** with AI extraction
- **Template matching** against standard contract templates
- **Risk flagging** for problematic terms
- **Multi-model LLM support** (Groq, OpenAI, Anthropic, Google Gemini)
- **Voice input/output** (speech-to-text + text-to-speech)
- **Document annotations** (highlight, comment, strikeout, underline)
- **Multi-lingual support** with language detection
- **AI Agent** with 8 tools (email, files, web search, calendar)
- **Team collaboration** with organizations, roles, and shared document libraries
- **Enterprise SSO** (SAML 2.0)
- **Billing** via Stripe subscriptions
- **Webhook integrations**
- **Audit logging** for compliance
- **Data retention policies** (GDPR-ready)
- **GDPR Right to Delete** endpoint

---

# 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React/Vite)                         │
│              Vite Dev Server :5173 / Nginx Prod :80                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐│
│  │ Landing   │  │   Chat    │  │ Documents │  │ Clause Library   ││
│  │ Register  │  │(Streaming)│  │ Upload    │  │ Agent            ││
│  │ Login     │  │ Voice     │  │ Annotate  │  │ Templates        ││
│  └───────────┘  └───────────┘  └───────────┘  └──────────────────┘│
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐│
│  │ Comparison│  │ Summarize │  │Obligations│  │ Admin Dashboard  ││
│  │ Org Mgmt  │  │ API Keys  │  │ Webhooks  │  │ Audit Logs       ││
│  └───────────┘  └───────────┘  └───────────┘  └──────────────────┘│
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI/Uvicorn)                       │
│                       :8000 (4 workers)                              │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  Auth    │  │  RAG     │  │  Agent   │  │  Search Engine     │ │
│  │  JWT+2FA │  │  Chain   │  │ 8 Tools  │  │  Hybrid+BM25+RRF   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  Billing │  │  Ingestion│  │  Memory  │  │  LLM Provider     │ │
│  │  Stripe  │  │  Chunking+│  │  3-tier  │  │  Groq/OpenAI/etc  │ │
│  └──────────┘  │  ChromaDB │  └──────────┘  └────────────────────┘ │
│                └──────────┘                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  Org     │  │  Audit   │  │ Webhooks │  │  SSO (SAML)       │ │
│  │  Service │  │  Logging │  │  +Events │  │  python3-saml      │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────────┘ │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────────┐
        ▼              ▼                   ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  PostgreSQL  │ │   ChromaDB   │ │   External APIs   │
│  (Asyncpg)   │ │  (Embedding  │ │  ┌──────────────┐│
│  Messages    │ │   Vectors)   │ │  │  Groq API   ││
│  Users       │ │  Per-user    │ │  │  OpenAI API ││
│  Orgs        │ │  Per-org     │ │  │  Anthropic  ││
│  Obligations │ │  Memory      │ │  │  Google AI  ││
│  Analytics   │ │  Collection  │ │  │  Stripe     ││
│  Audit Logs  │ │              │ │  │  DuckDuckGo ││
│  API Keys    │ │              │ │  └──────────────┘│
└──────────────┘ └──────────────┘ └──────────────────┘
```

---

# 3. Technology Stack

## Backend (Python 3.11)

| Category | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI | Async REST API with auto-docs |
| **Server** | Uvicorn | ASGI server (4 workers) |
| **Database ORM** | SQLAlchemy (Async) | PostgreSQL access |
| **Database** | PostgreSQL 16 | Relational data |
| **Migrations** | Alembic | Schema versioning |
| **Vector Store** | ChromaDB | Embedding storage & retrieval |
| **Auth** | python-jose (JWT), passlib (bcrypt) | Authentication |
| **Rate Limiting** | slowapi | Per-endpoint rate limits |
| **LLM Framework** | LangChain | Multi-provider LLM orchestration |
| **Embeddings** | HuggingFace (BAAI/bge-small-en-v1.5) | Text embeddings |
| **Hybrid Search** | rank-bm25 (BM25Okapi) | Keyword retrieval |
| **Cross-encoder** | sentence-transformers (cross-encoder/ms-marco-MiniLM-L-6-v2) | Re-ranking |
| **OCR** | pytesseract + pdf2image | Scanned PDF text extraction |
| **PDF** | pypdf, reportlab | PDF parsing & generation |
| **DOCX** | python-docx | Word document support |
| **Voice** | gTTS (TTS), Groq Whisper (STT) | Voice I/O |
| **Calendar** | ics library | .ics file generation |
| **TOTP/2FA** | pyotp + qrcode | Two-factor auth |
| **SAML** | python3-saml | Enterprise SSO |
| **Payments** | Stripe | Subscription billing |
| **Error Tracking** | Sentry SDK | Error monitoring |
| **Background** | asyncio | Async task management |

## Frontend (React 18)

| Category | Technology | Purpose |
|---|---|---|
| **Framework** | React 18 | UI library |
| **Build Tool** | Vite 5 | Fast dev/build |
| **Routing** | React Router v6 | Client-side routing |
| **HTTP** | Axios | API calls |
| **Icons** | Lucide React | Icon library |
| **Markdown** | react-markdown + remark-gfm | Render AI responses |
| **Notifications** | react-hot-toast | Toast notifications |
| **PDF Export** | html2pdf.js (client), reportlab (server) | PDF generation |
| **Styling** | Tailwind CSS 3 | Utility-first CSS |
| **E2E Tests** | Playwright | Browser tests |
| **Unit Tests** | Vitest + Testing Library | Component tests |
| **Dark Mode** | ThemeContext | Dark/light theme |
| **Sentry** | @sentry/react | Frontend error tracking |

## Infrastructure

| Category | Technology |
|---|---|
| **Containerization** | Docker, docker-compose |
| **Reverse Proxy** | Nginx (in frontend container) |
| **Database** | PostgreSQL 16 Alpine |
| **CI/CD** | GitHub Actions |

---

# 4. Backend Deep Dive

## 4.1 File Map (21 Python Modules)

| File | Lines | Purpose |
|---|---|---|
| `main.py` | 3,758 | App entry, all API endpoints, lifespan, seed data |
| `config.py` | 186 | Centralized configuration (env vars) |
| `database.py` | 426 | SQLAlchemy models, session management, init |
| `auth.py` | 358 | Registration, login, JWT, 2FA, RBAC |
| `rag_chain.py` | 493 | Full RAG pipeline: rewrite→retrieve→generate→score |
| `ingestion.py` | 344 | Document upload, text extraction, chunking, ChromaDB |
| `search_engine.py` | 300 | Hybrid search (semantic + BM25 + RRF + re-rank) |
| `llm_provider.py` | 127 | Multi-provider LLM factory (Groq/OpenAI/Anthropic/Google) |
| `memory_service.py` | 223 | 3-tier memory: recent, summary, long-term |
| `agent.py` | 299 | AI Agent orchestrator with full conversation history |
| `agent_tools.py` | 322 | 8 agent tools: email, files, web, calendar, summarize |
| `billing.py` | 345 | Stripe subscriptions, usage metering, plans |
| `organization.py` | 286 | Org CRUD, membership management, roles |
| `audit.py` | 128 | Audit log creation and retrieval |
| `webhooks.py` | 165 | Webhook registration, delivery, retry, HMAC signing |
| `sso.py` | 252 | SAML 2.0 SSO login flow |
| `retention.py` | 98 | Data retention policy enforcement |
| `language_utils.py` | 75 | Language detection (langdetect) |
| `analytics.py` | 81 | Admin dashboard stats |
| `websocket_manager.py` | 53 | WebSocket connection manager |
| `tenant.py` | 71 | Multi-tenant isolation utilities |
| `health_check.py` | 117 | DevOps health check CLI |
| `backup.py` | 173 | Backup script (pg_dump + ChromaDB snapshot) |
| `email_service.py` | 43 | Generic email sender |
| `legal_content.py` | 430 | ToS, Privacy Policy, DPA text |

## 4.2 Application Lifespan (`main.py`)

On startup, the `lifespan` async context manager:

1. **Initializes Sentry** if `SENTRY_DSN` is configured
2. **Runs Alembic migrations** to ensure DB schema is current
3. **Pre-loads embedding model** (BAAI/bge-small-en-v1.5) into memory
4. **Seeds standard contract templates** (NDA, Employment, SaaS, Vendor) if empty
5. **Applies data retention policies** for all orgs with non-zero retention days

## 4.3 Middleware

```python
# CORS - allows frontend origins
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS)

# HTTPS enforcement (production)
@app.middleware("http")
async def enforce_https: redirects http→https if x-forwarded-proto is http

# Rate limiting via slowapi
limiter = Limiter(key_func=get_remote_address)
```

---

# 5. Frontend Deep Dive

## 5.1 Pages (23 routes)

| Route | Component | Auth Required | Description |
|---|---|---|---|
| `/` | Landing.jsx | No | Marketing page with features, testimonials, pricing |
| `/login` | Login.jsx | No | Email/password login with 2FA support |
| `/register` | Register.jsx | No | User registration |
| `/chat` | Chat.jsx | Yes | Main AI chat with streaming, voice, doc filter |
| `/documents` | Documents.jsx | Yes | Upload, list, delete, annotate documents |
| `/extract-clauses` | ClauseExtractor.jsx | Yes | Extract specific clause types |
| `/compare-clauses` | ContractComparison.jsx | Yes | Side-by-side contract comparison |
| `/summarize` | DocumentSummary.jsx | Yes | AI document summarization |
| `/obligations` | ObligationTracker.jsx | Yes | Extract and track obligations |
| `/template-match` | TemplateMatch.jsx | Yes | Match docs against standard templates |
| `/clause-library` | ClauseLibrary.jsx | Yes | Save, share, benchmark clauses |
| `/agent` | Agent.jsx | Yes | AI agent with tools |
| `/profile` | Profile.jsx | Yes | User profile, avatar, 2FA setup |
| `/admin` | AdminDashboard.jsx | Admin | System analytics, user management |
| `/org/team` | TeamManagement.jsx | Org Member | Invite/manage team members |
| `/org/audit` | AuditLogs.jsx | Org Admin | View audit trail |
| `/org/keys` | APIKeys.jsx | Org Admin | API key management |
| `/org/settings` | OrgSettings.jsx | Org Admin | Branding, SSO, retention |
| `/terms` | TermsOfService.jsx | No | Legal ToS |
| `/privacy` | PrivacyPolicy.jsx | No | Privacy policy |
| `/dpa` | DPA.jsx | No | Data processing agreement |

## 5.2 Core Frontend Components (17)

| Component | Description |
|---|---|
| `Navbar` | Top navigation with branding, theme toggle, user menu |
| `Footer` | Site footer with links |
| `ProtectedRoute` | Redirects to login if unauthenticated |
| `AdminRoute` | Requires admin role |
| `ChatHistorySidebar` | Session management sidebar |
| `MessageBubble` | Renders chat messages with sources, confidence, risk flags |
| `UploadModal` | Document upload dialog |
| `SourceCard` | Displays document source citations |
| `RiskBadge` | Badge for risky terms |
| `DocumentViewer` | Inline document viewer with annotations |
| `LoadingSkeleton` | Shimmer loading placeholders |
| `Toast` | Toast notification system (react-hot-toast wrapper) |
| `CookieConsent` | GDPR cookie consent banner |
| `AIDisclaimer` (3 variants) | Disclaimer banners (banner, chat notice, floating) |
| `OnboardingTour` | First-time user tour guide |
| `DeleteDataModal` | GDPR data deletion confirmation |

## 5.3 State Management

- **AuthContext** — user state, token, branding, org roles
- **ThemeContext** — dark/light mode with Tailwind CSS
- Local state via `useState`/`useReducer` in each page

## 5.4 API Client (`api.js`)

Central Axios client with:
- **Auth interceptor** — attaches Bearer token from localStorage
- **401 interceptor** — auto-redirects to login on token expiry
- **30+ API functions** covering all backend endpoints

---

# 6. AI & LLM Integration

## 6.1 Multi-Provider Factory (`llm_provider.py`)

The `LLMProvider` class is a dynamic factory that supports 4 providers:

```python
_PROVIDER_REGISTRY = {
    "groq":     ("langchain_groq",     "ChatGroq",     "GROQ_API_KEY",     "GROQ_MODEL"),
    "openai":   ("langchain_openai",   "ChatOpenAI",   "OPENAI_API_KEY",   "OPENAI_MODEL"),
    "anthropic":("langchain_anthropic","ChatAnthropic","ANTHROPIC_API_KEY","ANTHROPIC_MODEL"),
    "google":   ("langchain_google_genai","ChatGoogleGenerativeAI","GOOGLE_API_KEY","GOOGLE_MODEL"),
}
```

**Key features:**
- Lazy imports — only loads the package for the requested provider
- Caching — caches LLM instances per `(provider, model, temperature, streaming)` key
- Graceful fallback — if a provider is unavailable, falls back to default
- `get_memory_llm()` — always uses Groq's fast `llama-3.1-8b-instant` model for cheap memory tasks

**Default models:**
- Groq: `llama-3.3-70b-versatile`
- OpenAI: `gpt-4o`
- Anthropic: `claude-sonnet-4-20250514`
- Google: `gemini-1.5-pro`

## 6.2 System Prompt

The legal system prompt (`config.py`) enforces:

1. **Source citation** — every statement cites `[Document: filename, Chunk: N]`
2. **No outside knowledge** — answers only from provided context
3. **Risk flagging** — alerts on unusual/one-sided clauses
4. **Privilege awareness** — marks attorney-client privileged content
5. **Mandatory disclaimer** — appended to every response
6. **Multi-language support** — responds in the user's detected language

---

# 7. RAG Pipeline (Core Intelligence)

The `RAGChain` class (`rag_chain.py`) implements a complete Retrieval-Augmented Generation pipeline:

```
User Question
     │
     ▼
┌──────────────────┐
│  1. Question     │  Only if >2 messages in session
│     Rewriter     │  LLM rewrites follow-up to be self-contained
└──────┬───────────┘
       ▼
┌──────────────────┐
│  2. Hybrid       │  Parallel semantic (ChromaDB) + BM25 search
│     Retrieval    │  Reciprocal Rank Fusion to merge results
│     (Search      │  Optional cross-encoder re-ranking for precision
│      Engine)     │
└──────┬───────────┘
       ▼
┌──────────────────┐
│  3. Context      │  Formats chunks with [Document, Chunk] citations
│     Assembly     │  Loads session summary + long-term memory
└──────┬───────────┘
       ▼
┌──────────────────┐
│  4. Answer       │  LangChain chain: system prompt + context → LLM
│     Generation   │  Uses selected provider (Groq/OpenAI/etc)
└──────┬───────────┘
       ▼
┌──────────────────┐
│  5. Risk         │  Scans chunks for 14+ risk terms
│     Flagging     │  LLM explains why each term is risky
└──────┬───────────┘
       ▼
┌──────────────────┐
│  6. Confidence   │  3-component score (0-100):
│     Scoring      │    - Retrieval relevance (re-ranker scores)
│                  │    - Source coverage (unique docs)
│                  │    - Answer coherence (LLM self-assessment)
│                  │  Label: High/Medium/Low
└──────┬───────────┘
       ▼
┌──────────────────┐
│  7. Persistence  │  Saves Q&A to PostgreSQL
│     + Analytics  │  Logs response time, sources used
└──────┬───────────┘
       ▼
┌──────────────────┐
│  8. Background   │  Extracts long-term memory facts
│     Memory       │  Updates session summary if ≥6 messages
└──────────────────┘
```

## 7.1 Risk Terms Detected

```python
RISK_TERMS = [
    "unlimited liability", "perpetual license", "irrevocable",
    "auto-renewal", "automatic renewal", "unilateral modification",
    "sole discretion", "non-compete", "non-solicitation",
    "indemnify and hold harmless", "waiver of jury trial",
    "class action waiver", "liquidated damages", "penalty clause",
    "evergreen clause",
]
```

## 7.2 Streaming Pipeline

The `/api/chat/stream` endpoint provides Server-Sent Events (SSE):

```
data: {"type": "meta", "session_id": "...", "sources": [...]}
data: {"type": "token", "token": "The"}
data: {"type": "token", "token": " agreement"}
...
data: {"type": "risk_flags", "risk_flags": ["auto-renewal"]}
data: {"type": "done", "response_time_ms": 1234}
```

---

# 8. Document Ingestion Pipeline

## 8.1 Supported Formats

- **TXT** — direct UTF-8 text extraction
- **PDF** — PyPDF text extraction + OCR fallback via Tesseract
- **DOCX** — python-docx paragraph extraction

## 8.2 Processing Flow

```
Upload → Validate → Extract Text → Chunk → Embed → Store
  │         │           │            │        │        │
  │    Allowed exts   txt/pdf/   Recursive   BGE      ChromaDB
  │    Size < 10MB    docx       Char        small     per-user
  │                              600 chars   v1.5     + per-org
  │                     OCR         │          │      collections
  │                  fallback    75 overlap   │
  │                  (Tesseract)              │
  │                                           │
  ▼                                           ▼
PostgreSQL                                 Vector DB
(Document metadata)                        (semantic search)
```

## 8.3 OCR Fallback

For scanned PDFs (no extractable text), the system:
1. Converts PDF pages to images via `pdf2image` (poppler-utils)
2. Runs `pytesseract` OCR on each page
3. Combines all OCR text as fallback content

## 8.4 Chunking Strategy

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=75,
    separators=["\n\n", "\n", ". ", " ", ""],
)
```

## 8.5 Storage Architecture

| Data | Storage | Purpose |
|---|---|---|
| Document metadata | PostgreSQL | Filename, size, date, owner |
| Text chunks (vectors) | ChromaDB (per-user) | Semantic search |
| Text chunks (org) | ChromaDB (per-org) | Org-wide shared docs |
| Full text | ChromaDB (retrievable) | Report generation |

---

# 9. Multi-Tenancy & Organizations

## 9.1 Organization Hierarchy

```
Organization
   ├── Owner (1, originally creator)
   ├── Admins (can manage members, settings)
   ├── Members (use shared resources)
   └── Viewers (read-only access)
```

## 9.2 Key Features

| Feature | Description |
|---|---|
| **Document Sharing** | Share personal docs to org library (moves to org ChromaDB) |
| **Team Invitations** | Invite by email, auto-provision placeholder users |
| **Role Management** | owner → admin → member → viewer hierarchy |
| **Custom Branding** | Logo, colors, custom domain (white-label) |
| **Custom System Prompt** | Org-specific LLM instructions |
| **Data Retention** | Per-org retention policy (days) |
| **SSO** | SAML 2.0 per org |
| **Subscription** | Org-level billing (owner's plan applies to all) |

## 9.3 Tenant Isolation (`tenant.py`)

The system uses **soft isolation** (shared PostgreSQL with org_id FK, separate ChromaDB collections):

```python
- documents:   org-scoped (visible to all org members if shared)
- messages:    user-scoped (private to each user)
- obligations: user-scoped
- clauses:     org-scoped if shared to org library
- chromadb:    separate collections per user/org
- database:    shared PostgreSQL with org_id FK
```

---

# 10. Enterprise Features

## 10.1 API Key Management

- **Prefix:** `lxb_` + 24 bytes hex (48 chars)
- **Hashed** (SHA-256) in database — never stored in plaintext
- **Rate limits:** configurable RPM (default 60) and RPD (default 1000)
- **Expiry:** optional TTL in days
- **Scopes:** JSON array of allowed endpoints
- **Usage tracking:** auto-incremented counter, last used timestamp

## 10.2 Webhook System

| Feature | Implementation |
|---|---|
| **Registration** | URL + event types + optional secret |
| **Event types** | `query.completed`, `document.uploaded`, `document.deleted`, `member.invited`, `member.role_changed`, `member.removed`, `member.left`, `settings.update`, `document.shared` |
| **Wildcard** | `"*"` subscribes to all events |
| **Delivery** | Async via `asyncio.create_task` |
| **Retry** | 3 attempts with exponential backoff (2s, 4s, 8s) |
| **HMAC Signing** | SHA-256 signature in `X-LexBot-Signature` header |
| **Auto-disable** | After 5 consecutive failures |
| **Test endpoint** | Sends `test.ping` event |

## 10.3 SAML SSO

- **Provider-agnostic** — works with any SAML 2.0 IdP
- **Simulation mode** — when `python3-saml` is not installed (generates mock login URLs)
- **Auto-provisioning** — creates users on first SAML login
- **Org membership** — auto-joins to correct organization

## 10.4 Data Retention

- **Per-org policy** — configurable number of days (0 = forever)
- **Scope:** Messages, summaries, long-term memory, analytics, audit logs
- **Enforcement:** On startup + manual trigger via API
- **Deletion scope:** All data older than cutoff date for org members

## 10.5 Client Portal

Lawyers can share documents with external clients:

- Share by email or user_id
- Configurable permissions (can ask questions)
- Optional expiry (auto-revoke after N days)
- Client role users only see shared documents

## 10.6 White-Label Branding

- Per-org logo upload (stored in `static/logos/`)
- Primary/secondary colors (injected via CSS variables)
- Custom domain support
- Custom system prompt for org-specific LLM behavior

---

# 11. Billing & Subscription System

## 11.1 Plans

| Feature | Free | Professional | Enterprise |
|---|---|---|---|
| **Max Documents** | 5 | 100 | 999,999 |
| **Monthly Queries** | 50 | 10,000 | 999,999 |
| **Max File Size** | 10 MB | 50 MB | 100 MB |
| **Chat** | ✓ | ✓ | ✓ |
| **Documents** | ✓ | ✓ | ✓ |
| **Summarize** | ✓ | ✓ | ✓ |
| **Extract Clauses** | ✓ | ✓ | ✓ |
| **Compare Clauses** | ✓ | ✓ | ✓ |
| **Template Match** | ✓ | ✓ | ✓ |
| **Obligations** | ✓ | ✓ | ✓ |
| **Clause Library** | ✓ | ✓ | ✓ |
| **Annotations** | ✓ | ✓ | ✓ |
| **API Access** | ✗ | ✓ | ✓ |
| **SSO** | ✗ | ✗ | ✓ |
| **Custom Branding** | ✗ | ✗ | ✓ |

## 11.2 Stripe Integration

| Operation | Implementation |
|---|---|
| **Checkout** | Creates Stripe Checkout Session → redirects to Stripe |
| **Portal** | Creates Billing Portal Session (manage subscription) |
| **Customer** | Auto-creates Stripe Customer (lazy) |
| **Webhooks** | `checkout.session.completed`, `invoice.paid`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed` |
| **Trialing** | 14-day free trial |
| **Demo mode** | Works without Stripe keys (returns mock URLs) |

## 11.3 Usage Metering

- **Query counting** — monthly aggregate of `Analytics` table entries
- **Document counting** — monthly aggregate of `Document` table entries
- **Organization aggregation** — if user is in an org, usage is summed across all members
- **Feature gating** — `check_feature_access()` checks feature availability + query limits

---

# 12. Agent System

## 12.1 Architecture

```
User Command
     │
     ▼
┌──────────────────────┐
│ Agent System Prompt  │  With tool descriptions dynamically inserted
│    + Full History    │  (up to 20 recent messages from DB)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  LLM (Groq) decides  │  Returns JSON: {"tool": "...", "parameters": {...}}
│  tool or direct reply │  or {"tool": "none", "answer": "..."}
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌──────────┐ ┌──────────┐
│ Execute  │ │ Direct   │
│ Tool     │ │ Answer   │
└────┬─────┘ └──────────┘
     │
     ▼
┌──────────────────────┐
│ Save to DB (human +  │  Full conversation history preserved
│ assistant messages)  │
└──────────────────────┘
```

## 12.2 Available Tools (8)

| Tool | Description | Parameters |
|---|---|---|
| `send_email` | Send email via Gmail SMTP | to, subject, body, cc |
| `draft_email` | Draft email (no send) | to, subject, body |
| `open_file` | Read files from sandbox | file_path |
| `create_file` | Create txt/docx files | file_path, content, file_type |
| `list_directory` | List files in sandbox | directory_path, extension_filter |
| `web_search` | DuckDuckGo web search | query, max_results |
| `create_reminder` | Create .ics calendar file | title, date, description, output_path |
| `summarize_document` | Summarize uploaded LexBot doc | document_name |

## 12.3 Safety

- **Sandboxed file access** — all file operations restricted to `data/agent_files/`
- **Path traversal protection** — `_safe_path()` validates resolved path is within sandbox
- **Email confirmation** — `draft_email()` must be used first unless user explicitly says "send"

---

# 13. Memory System

## 13.1 Three-Tier Architecture

```
MemoryService
  │
  ├── Tier 1: Recent Messages (PostgreSQL)
  │   └── Last 10 messages per session
  │   └── Used for question rewriting context
  │
  ├── Tier 2: Session Summary (PostgreSQL)
  │   └── Auto-generated every 6 messages
  │   └── LLM summarizes conversation: docs reviewed, key findings
  │   └── Included in system prompt for all subsequent queries
  │
  └── Tier 3: Long-Term Memory (PostgreSQL + ChromaDB)
      └── Extracted from every Q&A (if a fact worth remembering)
      └── Stored in both SQLite and ChromaDB for semantic retrieval
      └── Top 5 relevant facts injected into system prompt
```

## 13.2 Fact Extraction

After every Q&A pair, the system asks a Groq LLM:
> "Extract ONE important legal fact worth remembering long-term"

If it responds with something other than `NONE`, the fact is:
1. Saved to PostgreSQL `long_term_memory` table
2. Vectorized and stored in per-user ChromaDB memory collection

## 13.3 Session Clear

Users can clear all memory for a session (messages + summary) via the API.

---

# 14. Security, Compliance & Legal

## 14.1 Authentication

| Mechanism | Implementation |
|---|---|
| **Password hashing** | bcrypt via passlib |
| **JWT tokens** | HS256, 8-hour expiry |
| **2FA** | TOTP via pyotp, QR code provisioning |
| **Rate limiting** | 5/min register, 10/min login |
| **Password rules** | 8+ chars, uppercase, lowercase, digit |

## 14.2 Authorization (RBAC)

| Role | Scope |
|---|---|
| **Admin** | System-wide: view/ deactivate/ promote users, analytics |
| **Org Owner** | Full org control, billing |
| **Org Admin** | Manage members, settings, webhooks, API keys |
| **Org Member** | Access shared resources |
| **Viewer** | Read-only org access |
| **Client** | Access only shared documents |
| **User** (default) | Personal document access |

## 14.3 Data Protection

- **Encryption in transit:** TLS 1.3 (via Nginx/HTTPS middleware)
- **Encryption at rest:** AES-256 (database level)
- **Password storage:** bcrypt hashing (never plaintext)
- **API keys:** SHA-256 hashed in DB (never plaintext)
- **Document storage:** ChromaDB with per-user/org isolation

## 14.4 Privacy Compliance

| Feature | GDPR | CCPA |
|---|---|---|
| **Right to Delete** | `POST /api/account/delete-my-data` | ✓ |
| **Data Processing Agreement** | `/api/legal/dpa` | ✓ |
| **Privacy Policy** | `/api/legal/privacy` | ✓ |
| **Data Retention Policies** | Configurable per-org | ✓ |
| **Data Portability** | PDF export of sessions | ✓ |
| **Cookie Consent** | `CookieConsent` component | ✓ |
| **Sub-processor List** | Schedule B in DPA (7 sub-processors) | ✓ |
| **Data Breach Notification** | 48-hour notification (DPA clause) | ✓ |
| **Audit Rights** | SOC 2 Type II + annual audits (DPA) | ✓ |

## 14.5 Legal Content

The project includes full legal documents as code (`legal_content.py`):

- **Terms of Service** — 15 sections covering acceptance, service description, liability, IP, billing, termination, governing law
- **Privacy Policy** — 13 sections covering data collection, processing basis (GDPR), rights (GDPR/CCPA), security, international transfers, cookies
- **Data Processing Agreement (DPA)** — 10 sections + 2 schedules covering processor obligations, sub-processors, breach notification, security measures, audit rights
- **AI Disclaimer** — Professional, neutral warning that AI output is not legal advice

## 14.6 Audit Logging

Every significant action is logged:

```python
actions tracked: [
    "query.ask", "document.upload", "document.delete", "document.share",
    "document.privilege_update", "org.create", "settings.update",
    "member.invite", "member.role_change", "member.remove", "member.leave",
    "api_key.create", "api_key.revoke", "webhook.create", "webhook.delete",
    "webhook.test", "sso.configure", "retention.run",
    "settings.branding_logo", "user.sso_login", "agent.command",
]
```

Each audit entry includes: org_id, user_id, action, resource_type, resource_id, details (JSON), IP address, user agent, timestamp.

---

# 15. Search Engine

## 15.1 Three-Stage Hybrid Search

```
                   User Query
                       │
                       ▼
              ┌─────────────────┐
              │  Stage 1:       │
              │  Semantic + BM25│
              │  (Parallel)     │
              └────────┬────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   ┌──────────────┐          ┌──────────────┐
   │  ChromaDB    │          │  BM25Okapi   │
   │  (BGE-small  │          │  (Tokenized  │
   │   embeddings)│          │   keyword)   │
   │  Top 10 docs │          │  Top 10 docs │
   └──────┬───────┘          └──────┬───────┘
          │                         │
          └────────────┬────────────┘
                       ▼
              ┌─────────────────┐
              │  Stage 2:       │
              │  RRF Merge      │
              │  (Reciprocal    │
              │   Rank Fusion)  │
              │  Weight: 0.7s/  │
              │   0.3k + RRF k60│
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Stage 3:       │
              │  Cross-Encoder  │
              │  Re-ranking     │
              │  (MiniLM-L-6-v2)│
              │  Top 4 docs     │
              └─────────────────┘
```

## 15.2 BM25 Index Management

- **Per-user and per-org indexes** (keyed as `user_42` or `org_5`)
- **5-minute TTL cache** — auto-refreshes on access
- **Manual invalidation** — triggered on document upload/delete/share
- **Lazy building** — built only when first queried

## 15.3 Cross-Encoder Re-ranking

- **Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Lazy-loaded** — only loaded on first re-rank request
- **Graceful fallback** — if cross-encoder fails/unavailable, uses position-based scores
- **Precision boost** — significantly improves top-k relevance

---

# 16. Database Schema

## 16.1 Tables (17 models)

| Table | Key Columns | Purpose |
|---|---|---|
| `users` | id, username, email, hashed_password, role, org_id, 2fa, stripe | User accounts |
| `organizations` | id, name, slug, owner_id, branding, custom_domain, sso | Multi-tenant orgs |
| `org_memberships` | org_id, user_id, role, is_active, invited_by | Org membership |
| `documents` | id, user_id, org_id, filename, chunks, characters, is_privileged | Document records |
| `messages` | id, user_id, session_id, role, content | Chat messages |
| `summaries` | user_id, session_id, summary | Session summaries |
| `long_term_memory` | user_id, memory_text | Extracted facts |
| `analytics` | user_id, question, response_time_ms, sources_used | Query analytics |
| `feature_usage` | user_id, feature_name, clause_type | Feature tracking |
| `obligations` | user_id, document_id, text, party, deadline, type, status | Extracted obligations |
| `contract_templates` | user_id, org_id, name, type, clauses_json | Standard/custom templates |
| `saved_clauses` | user_id, org_id, type, content, is_benchmark | Clause library |
| `document_annotations` | user_id, document_id, type, page, text, comment, color, position | Annotations |
| `invoices` | user_id, stripe_invoice_id, amount, status | Billing invoices |
| `audit_logs` | org_id, user_id, action, resource, details, ip | Audit trail |
| `api_keys` | org_id, user_id, key_hash, scopes, rate_limits | API access |
| `webhook_endpoints` | org_id, url, secret, events_json, failure_count | Webhook config |
| `doc_shares` | document_id, client_user_id, can_ask, expires_at | Client portal |
| `notifications` | user_id, title, body, type, resource, is_read | In-app notifications |

## 16.2 Indexes

Key performance indexes on:
- `idx_org_memberships_org_user` — unique composite (org + user)
- `idx_documents_user_filename` — fast user document lookup
- `idx_messages_user_session` — session message retrieval
- `idx_audit_logs_org_id` + `idx_audit_logs_created_at` — audit queries
- `idx_api_keys_org_id` — org key listing
- `idx_webhooks_org_id` — org webhook listing
- `idx_notifications_user_read` — unread notification queries

---

# 17. API Endpoint Reference

## 17.1 Authentication (7 endpoints)

| Method | Path | Auth | Rate Limit | Description |
|---|---|---|---|---|
| POST | `/api/auth/register` | No | 5/min | Create account |
| POST | `/api/auth/login` | No | 10/min | Login (returns JWT) |
| GET | `/api/auth/me` | Bearer | — | Current user profile |
| PATCH | `/api/auth/me` | Bearer | — | Update profile |
| POST | `/api/auth/avatar` | Bearer | — | Upload avatar |
| POST | `/api/auth/2fa/setup` | Bearer | — | Setup TOTP |
| POST | `/api/auth/2fa/verify` | Bearer | — | Verify TOTP code |
| POST | `/api/auth/2fa/disable` | Bearer | — | Disable 2FA |
| POST | `/api/auth/2fa/login` | No | 10/min | 2FA login step |

## 17.2 Chat (2 endpoints)

| Method | Path | Description |
|---|---|---|
| POST | `/api/chat` | Full response with RAG, sources, risk flags, confidence |
| POST | `/api/chat/stream` | SSE streaming response |

## 17.3 Documents (7 endpoints)

| Method | Path | Description |
|---|---|---|
| POST | `/api/upload` | Upload document (txt/pdf/docx) |
| GET | `/api/documents` | List user's documents (paginated) |
| DELETE | `/api/documents/{id}` | Delete document |
| PATCH | `/api/documents/{id}/privilege` | Toggle privilege status |
| GET | `/api/documents/privileged` | List privileged docs |
| POST | `/api/documents/{id}/share` | Share to org |
| GET | `/api/org/documents` | List org documents |

## 17.4 AI Features (8 endpoints)

| Method | Path | Feature |
|---|---|---|
| POST | `/api/extract-clauses` | Extract specific clause type |
| POST | `/api/compare-clauses` | Compare clauses across docs |
| POST | `/api/summarize` | Document summarization (brief/detailed/executive) |
| POST | `/api/obligations/extract` | Extract obligations |
| POST | `/api/timeline` | Extract timeline events |
| POST | `/api/cross-reference` | Multi-document search |
| POST | `/api/extract-tables` | Extract tabular data |
| POST | `/api/templates/match` | Template compliance check |

## 17.5 Templates & Clauses (10 endpoints)

| Method | Path | Description |
|---|---|---|
| GET | `/api/templates` | List templates |
| POST | `/api/templates/create` | Create custom template |
| PUT | `/api/templates/{id}` | Update template |
| DELETE | `/api/templates/{id}` | Delete template |
| POST | `/api/templates/match` | Match doc against template |
| POST | `/api/clauses/save` | Save clause to library |
| GET | `/api/clauses` | List clauses |
| DELETE | `/api/clauses/{id}` | Delete clause |
| POST | `/api/clauses/{id}/share` | Share clause to org |
| PATCH | `/api/clauses/{id}/benchmark` | Toggle benchmark |

## 17.6 Obligations (4 endpoints)

| Method | Path | Description |
|---|---|---|
| POST | `/api/obligations` | Extract obligations (v2 - JSON parsing) |
| GET | `/api/obligations` | List obligations |
| PATCH | `/api/obligations/{id}/status` | Update status |
| DELETE | `/api/obligations/{id}` | Delete obligation |
| GET | `/api/obligations/export` | Export as CSV |

## 17.7 Annotations (5 endpoints)

| Method | Path | Description |
|---|---|---|
| POST | `/api/annotations` | Create annotation |
| GET | `/api/annotations` | List annotations |
| PATCH | `/api/annotations/{id}` | Update annotation |
| DELETE | `/api/annotations/{id}` | Delete annotation |
| GET | `/api/export/document/{id}/annotated` | Export annotated PDF |

## 17.8 Voice (2 endpoints)

| Method | Path | Description |
|---|---|---|
| POST | `/api/voice/transcribe` | Speech-to-text (Groq Whisper) |
| POST | `/api/voice/speak` | Text-to-speech (gTTS) |

## 17.9 Billing (5 endpoints)

| Method | Path | Description |
|---|---|---|
| POST | `/api/billing/create-checkout` | Stripe checkout session |
| POST | `/api/billing/portal` | Stripe billing portal |
| GET | `/api/billing/subscription` | Current plan + usage |
| GET | `/api/billing/invoices` | Invoice history |
| POST | `/api/billing/webhook` | Stripe webhook handler |

## 17.10 Organization (14 endpoints)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/org` | User | Create org |
| GET | `/api/org` | Org Member | Get org details |
| PATCH | `/api/org/settings` | Org Admin | Update settings |
| POST | `/api/org/invite` | Org Admin | Invite member |
| GET | `/api/org/members` | Org Member | List members |
| PATCH | `/api/org/members/{id}/role` | Org Admin | Change role |
| DELETE | `/api/org/members/{id}` | Org Admin | Remove member |
| POST | `/api/org/leave` | Org Member | Leave org |
| POST | `/api/org/api-keys` | Org Admin | Create API key |
| GET | `/api/org/api-keys` | Org Member | List API keys |
| DELETE | `/api/org/api-keys/{id}` | Org Admin | Revoke API key |
| GET | `/api/org/api-keys/usage` | Org Admin | Usage stats |
| POST | `/api/org/webhooks` | Org Admin | Create webhook |
| GET | `/api/org/webhooks` | Org Member | List webhooks |
| DELETE | `/api/org/webhooks/{id}` | Org Admin | Delete webhook |
| POST | `/api/org/webhooks/{id}/test` | Org Admin | Test webhook |
| POST | `/api/org/retention/run` | Org Admin | Run retention policy |
| POST | `/api/org/sso/configure` | Org Admin | Configure SSO |
| POST | `/api/org/branding/logo` | Org Admin | Upload logo |
| GET | `/api/org/isolation` | Org Admin | Isolation report |

## 17.11 Admin (4 endpoints)

| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/analytics` | System stats |
| GET | `/api/admin/users` | List all users |
| PATCH | `/api/admin/users/{id}/deactivate` | Deactivate user |
| POST | `/api/admin/users/{id}/promote` | Promote to admin |

## 17.12 Agent (2 endpoints)

| Method | Path | Description |
|---|---|---|
| POST | `/api/agent` | Execute agent command |
| GET | `/api/agent/tools` | List available tools |

## 17.13 Legal/Compliance (5 endpoints)

| Method | Path | Description |
|---|---|---|
| GET | `/api/legal/terms` | Terms of Service |
| GET | `/api/legal/privacy` | Privacy Policy |
| GET | `/api/legal/dpa` | Data Processing Agreement |
| GET | `/api/legal/disclaimer` | AI disclaimer |
| GET | `/api/legal/versions` | Legal doc versions |
| POST | `/api/account/delete-my-data` | GDPR Right to Delete |

## 17.14 Other (5 endpoints)

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/providers` | Available LLM providers |
| GET | `/api/memory/{session_id}` | Session memory |
| DELETE | `/api/memory/{session_id}` | Clear session memory |
| POST | `/api/language/detect` | Language detection |
| GET | `/api/languages` | Supported languages |
| GET | `/api/export/session/{session_id}` | Export session as PDF |

---

# 18. DevOps & Deployment

## 18.1 Docker Compose

```yaml
services:
  db:       postgres:16-alpine (port 5432)
  backend:  Python FastAPI (port 8000, 4 workers)
  frontend: Nginx serving React build (port 80)
volumes:    pgdata, chroma_data
```

## 18.2 Backend Dockerfile

Two-stage build:
1. **Builder:** Installs all Python dependencies + torch (CPU) + OCR tools
2. **Runtime:** Slim image with only runtime libs

## 18.3 Frontend Dockerfile

Builds React app with Vite, serves with Nginx (includes custom nginx.conf for API proxying)

## 18.4 Health Check CLI (`health_check.py`)

```bash
python health_check.py          # Human-readable output
python health_check.py --json   # JSON output for monitoring
```

Checks:
- All packages installed
- Required env vars configured
- Project directory structure intact

## 18.5 Backup Script (`backup.py`)

```bash
python backup.py                          # Full backup
python backup.py --db-only                # PostgreSQL only
python backup.py --chroma-only            # ChromaDB only
python backup.py --output /path/to/backups
```

Produces: `lexbot_backup_YYYYMMDD_HHMMSS.tar.gz` containing:
- `lexbot_db.sql` (pg_dump output)
- `chroma_db/` (directory snapshot)

## 18.6 CI/CD (`.github/workflows/ci.yml`)

GitHub Actions CI pipeline runs:
- `pip install -r requirements.txt`
- `pytest tests/`

---

# 19. Testing Strategy

## 19.1 Backend Tests (17 test files)

| File | Focus |
|---|---|
| `test_auth.py` | Registration, login, JWT, user retrieval |
| `test_agent_tools.py` | Email draft, file ops, web search, reminders |
| `test_analytics.py` | Admin stats aggregation |
| `test_audit.py` | Audit logging and retrieval |
| `test_billing.py` | Plan determination, usage metering, feature access |
| `test_config.py` | Configuration loading |
| `test_database.py` | DB operations, user CRUD |
| `test_health_check.py` | Health check CLI |
| `test_language_utils.py` | Language detection |
| `test_llm_provider.py` | Provider factory, fallbacks |
| `test_organization.py` | Org CRUD, membership, roles |
| `test_retention.py` | Data retention policy enforcement |
| `test_webhooks.py` | Registration, delivery, status |
| `test_api_routes.py` | Integration tests for API endpoints |

## 19.2 Frontend Tests (5 test files)

| File | Type |
|---|---|
| `api.test.jsx` | API client unit tests (Vitest) |
| `components.test.jsx` | Component rendering tests |
| `AuthContext.test.jsx` | Auth context unit tests |
| `ThemeContext.test.jsx` | Theme context unit tests |
| `e2e/` | Playwright end-to-end tests |

---

# 20. Feature Roadmap by Phase

## Phase 1 — Core (Complete)
- ✅ FastAPI backend + React frontend
- ✅ Document upload (PDF, DOCX, TXT)
- ✅ ChromaDB vector store
- ✅ Basic RAG chat with source citations
- ✅ JWT authentication

## Phase 2 — Intelligence (Complete)
- ✅ Clause extraction (10 types)
- ✅ Contract comparison
- ✅ Risk flagging (15 risk terms)
- ✅ Confidence scoring (3-component)
- ✅ Question rewriting
- ✅ Multi-language detection + response
- ✅ Voice input (Whisper STT)
- ✅ Voice output (gTTS TTS)
- ✅ Document annotations (4 types)
- ✅ Annotated PDF export
- ✅ Language endpoint

## Phase 3 — Session & Memory (Complete)
- ✅ 3-tier memory (recent, summary, long-term)
- ✅ Long-term fact extraction
- ✅ Session management
- ✅ Chat history export (PDF)
- ✅ Privileged document marking
- ✅ 2FA (TOTP)
- ✅ OCR for scanned PDFs

## Phase 4 — Advanced Features (Complete)
- ✅ Document summarization (3 styles)
- ✅ Obligation extraction + tracking
- ✅ Template matching (compliance scores)
- ✅ Table extraction
- ✅ Clause library + benchmarking
- ✅ Custom templates
- ✅ Multi-model LLM support (4 providers)
- ✅ Document filter in chat
- ✅ Streaming responses (SSE)
- ✅ Client portal (share docs externally)

## Phase 5 — Monetization (Complete)
- ✅ Stripe subscription integration
- ✅ 3-tier pricing (Free/Pro/Enterprise)
- ✅ Usage metering (queries, documents)
- ✅ Feature gating per plan
- ✅ Checkout + billing portal
- ✅ Invoice tracking
- ✅ Stripe webhook handling
- ✅ Demo mode (works without Stripe)

## Phase 6 — Enterprise (Complete)
- ✅ Multi-tenancy (organizations)
- ✅ Team management (roles & permissions)
- ✅ Document sharing within orgs
- ✅ Org-scoped ChromaDB collections
- ✅ Custom branding (white-label)
- ✅ Custom system prompts
- ✅ Custom domains
- ✅ API key management
- ✅ Rate limiting (per-key)
- ✅ Webhook system (8 event types)
- ✅ SAML SSO (with simulation mode)
- ✅ Audit logging (17 action types)
- ✅ Data retention policies
- ✅ Automated retention enforcement
- ✅ Tenant isolation utilities
- ✅ Real-time notifications (WebSocket)
- ✅ Agent system (8 tools)
- ✅ Full compliance (GDPR, CCPA)
- ✅ SOC 2 readiness documentation

## Planned / In Progress
- 🚧 Celery for background task queue
- 🚧 Redis for caching and rate limiting
- 🚧 Advanced RAG (GraphRAG, Agentic RAG)
- 🚧 Multi-vector retrieval
- 🚧 Enhanced client portal
- 🚧 Advanced analytics dashboards

---

# Summary

LexBot 3.0 is a **comprehensive, production-grade legal document AI platform** built with modern async Python and React. It combines:

- **State-of-the-art RAG** with hybrid search, re-ranking, confidence scoring, and multi-model support
- **Enterprise-grade multi-tenancy** with orgs, roles, SSO, audit logs, and webhooks
- **Full compliance** with GDPR, CCPA, and legal industry requirements
- **Professional AI safeguards** including source citation, risk flagging, privilege awareness, and mandatory disclaimers
- **Modern DevOps** with Docker, CI/CD, backup scripts, and health checks
- **Complete billing system** with Stripe integration and usage metering

The architecture is designed for **law firms of all sizes** — from solo practitioners to large corporate legal departments — with clear upgrade paths from free tier through enterprise.

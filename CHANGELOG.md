# Changelog

## 3.0.0 (2026-07-06)

### Highlights

- Full RAG pipeline with pgvector (replaced ChromaDB)
- Multi-provider LLM abstraction (Groq, OpenAI, Anthropic, Google)
- Agent system with 9 tools (summarize, email, web search, reminders, etc.)
- Voice I/O (Speech-to-Text + Text-to-Speech)
- Multi-tenant organizations with RBAC (owner/admin/member/viewer)
- Stripe billing (Free / Professional / Enterprise plans)
- SSO/SAML 2.0 (Okta, Azure AD)
- Document annotations, clause library, template matching
- 2FA/TOTP authentication
- Privilege-locked document sharing
- Partner API rate limits with API keys
- Celery + WebSockets infrastructure
- Client portal scaffolding
- SOC 2 readiness documentation

### Commits

```

c486973 — Migrate from ChromaDB to pgvector + add deployment configs (Vercel/Render/Supabase)

- Replaced ChromaDB vector store with PostgreSQL pgvector
- Added deployment configuration for Vercel, Render, and Supabase
- Updated CI pipeline for pgvector compatibility

a07709f — Agent system: create/manage AI agents with custom prompts, knowledge bases, and tool access

- Added agent CRUD endpoints
- Tool-based execution framework (9 tools)
- Custom knowledge base attachments per agent

15878b7 — Complete Plan 2-4 features: voice, annotations, templates, clause library, multilingual, 2FA, privilege lock, PostgreSQL migration, multi-tenant, partner API rate limits, Celery+WebSockets, client portal

- Voice I/O (Whisper STT, browser + server TTS)
- Document annotations CRUD
- Contract template matching with compliance scoring
- Clause library (save, search, filter, benchmark)
- Multi-language detection and translation support
- 2FA/TOTP setup and verification
- Privilege-locked documents (attorney-client privilege)
- Full PostgreSQL migration (removed SQLite)
- Multi-tenant organizations with membership roles
- Partner API key scoping and rate limits
- Celery + WebSockets infrastructure setup
- Client portal frontend scaffold
- White-screen bug fixes

f9a99e6 — CI: lazy import for embeddings, split sentence-transformers to optional

- Lazy-loaded embedding model to speed up cold starts
- Made sentence-transformers an optional dependency

4d8d255 — Dockerfile: add xmlsec1 deps for python3-saml build

- Added xmlsec1 system dependency for SAML authentication library

7789fb4 — Fix CI: add xmlsec1 deps for python3-saml, skip Playwright browser download

- CI fix for SAML library build
- Skipped Playwright browser download in CI pipeline

1a15aea — Update .dockerignore to exclude tests/data from Docker build

- Reduced Docker build context size

e1b1849 — Fix ruff lint errors and CI workflow

- Code style fixes
- CI pipeline stabilization

0e73dc6 — Initial commit: LexBot 3.0 legal-AI assistant

- FastAPI backend with SQLAlchemy ORM
- React 18 + Vite frontend
- Document upload and management
- JWT authentication
- Basic RAG pipeline with ChromaDB
- Chat interface with source citations
- Clause extraction and contract comparison
- Stripe billing integration
- Docker + Docker Compose setup
```

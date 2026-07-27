# Viva Q&A Preparation — LexBot

> Answer these concisely during the viva. Each entry has the likely question, a short answer, and the deeper technical detail to expand if the examiner probes further.

---

## Architecture & Design

### Q: Why FastAPI over Django?

**Short:** Django is monolithic and opinionated; FastAPI is async-native, auto-generates OpenAPI docs, and has first-class Pydantic validation — critical for an AI-intensive app with many LLM request/response schemas.

**Deep:** LexBot maxes async IO (DB queries, LLM calls, embedding generation). FastAPI's `async def` endpoints give us concurrency without thread pools. Django REST Framework would need DRF + async extensions + separate schema tooling. FastAPI's dependency injection also simplified auth middleware and rate-limit scoping per route.

### Q: Why pgvector over ChromaDB? (Commit `c486973`)

**Short:** We started with ChromaDB for prototyping but migrated to pgvector to eliminate a separate vector database — reducing operational complexity, enabling transactional consistency (DOCUMENTS and their chunks live in the same DB), and supporting ACID rollbacks during document deletion.

**Deep:** ChromaDB had no built-in auth, no transaction support, and required a separate backup strategy. pgvector gives us:
- ACID: If chunk insert fails mid-batch, the whole document upload rolls back
- JOINs: `DocumentChunk` can JOIN with `Document` for filtering by org/visibility/privilege in a single query
- Index types: IVFFlat for dev, HNSW for prod — tunable at the SQL level
- MFA: Same PostgreSQL backup/restore for everything

### Q: How does the RAG pipeline work?

**Answer:**
1. **Ingestion**: Uploaded PDF/DOCX/TXT is parsed (pdfplumber/python-docx), split into ~500-char overlapping chunks (LangChain `RecursiveCharacterTextSplitter`).
2. **Embedding**: Each chunk is embedded via Sentence-Transformers `all-MiniLM-L6-v2` (384-dim).
3. **Storage**: Chunk + embedding stored in `document_chunks` table with pgvector.
4. **Query**: User question is embedded with the same model → cosine similarity search → top-K chunks retrieved.
5. **Augmentation**: Retrieved chunks are injected into the LLM prompt as context.
6. **Generation**: LLM (Groq/OpenAI/Anthropic/Google) answers with citations and source references.

**File:** `backend/rag.py`

### Q: What chunking strategy did you use and why?

**Short:** 500-character chunks with 100-character overlap using `RecursiveCharacterTextSplitter`. This balances semantic coherence vs. retrieval granularity.

**Deep:**
- Too large (>1000 chars) → context windows fill with irrelevant content, degrading LLM answer quality.
- Too small (<200 chars) → chunks lack semantic context; the LLM hallucinates.
- Overlap prevents information loss at chunk boundaries (e.g., a clause split across two chunks still appears complete in at least one).
- We split by `["\n\n", "\n", ". ", " ", ""]` — paragraph first, then sentence, then word — trying to keep semantic units intact.

### Q: Why Sentence-Transformers over OpenAI Embeddings?

**Short:** Cost, latency, and data privacy. Self-hosting `all-MiniLM-L6-v2` means zero API cost, ~5ms per embedding (vs. ~200ms API call), and no document content ever leaves our server.

**Deep:** For a legal app, data residency matters. Sending contracts to a third-party embedding API raises confidentiality concerns. Self-hosted local embeddings also work offline (demo scenario, air-gapped deployments).

### Q: How is the multi-provider LLM abstraction implemented?

**Short:** A factory pattern in `backend/llm_provider.py` that returns a provider instance based on the `X-LLM-Provider` header. Each provider implements a common `BaseLLMProvider` interface with `generate()` and `generate_stream()` methods.

**Deep:** The `LLMProviderFactory` reads the header, maps it to a concrete class (`GroqProvider`, `OpenAIProvider`, `AnthropicProvider`, `GoogleProvider`), and returns the instance. This makes adding a new provider a single file change — implement the interface and register it in the factory. The RAG pipeline calls `provider.generate(prompt, context)` without caring which LLM is underneath.

---

## Security & Auth

### Q: How does authentication and authorization work?

**Short:** JWT (HS256) for session tokens. Role-based access at both the route level (FastAPI `Depends`) and component level (React `ProtectedRoute`). Multi-tenant resource scoping enforced in every database query.

**Deep:**
- **Register/Login** → bcrypt-hashed password → JWT access + refresh tokens (30 min / 7 days).
- **2FA**: TOTP based on `pyotp` — user scans QR, verifies once, gets a flag `is_2fa_enabled`. On login, if flagged, requires OTP.
- **SSO**: SAML 2.0 via `python3-saml` — org-level config stores IdP metadata; POST-binding for login, HTTP-Redirect for logout.
- **RBAC**: 4 roles — `owner` (full billing+member mgmt), `admin` (everything except billing), `member` (full features), `viewer` (read-only shared docs).
- **Tenancy**: Every query includes `WHERE organization_id = <current_org>` — enforced by a middleware that extracts org from the JWT.

### Q: How do you prevent data leaks between organizations?

**Short:** Database-level filtering. Every model has an `organization_id` FK, and every query is scoped via a middleware that adds the org from the JWT. No `SELECT *` without a WHERE clause on `organization_id`.

**Deep:** We also have:
- `visibility` on documents (private / org / public) — private docs are only visible to the uploader.
- `is_privileged` flag for attorney-client privilege — such documents never appear in shared org views.
- API keys are scoped to an org and optionally to specific permissions (read/write/admin).
- All endpoints verify membership via `OrgMembership` table before returning any data.

### Q: How are API keys secured?

**Short:** Keys are generated as `sk_live_<64-char-hex>` using `secrets.token_hex`, stored as bcrypt hash, and rate-limited per key (RPM/RPD limits stored in the `api_keys` table). The raw key is shown once at creation and never stored in plaintext.

---

## AI Agent

### Q: What tools does the agent have?

**Answer:** 9 tools:
1. `summarize` — Summarize a document
2. `email` — Send email (SMTP)
3. `web_search` — Real-time web search
4. `file_read` — Read files on server
5. `file_write` — Write files to disk
6. `reminder` — In-app reminders
7. `calendar` — Calendar check
8. `calculator` — Math evaluation
9. `weather` — Weather lookup

The agent uses a ReAct loop: Reason → Act → Observe → Repeat until the task is complete. Each tool is implemented as a separate function with a JSON schema defining its parameters.

### Q: Why a ReAct agent instead of a simple chain?

**Short:** Legal tasks are multi-step (e.g., "Summarize the contract and email the summary to my client"). A ReAct loop lets the LLM decide which tools to call, in what order, and whether the result is sufficient — without hardcoding a fixed pipeline.

---

## Billing

### Q: How does billing work?

**Short:** Stripe Checkout for subscription creation, Stripe Customer Portal for plan changes/cancellations. Webhooks sync Stripe events (checkout.session.completed, invoice.paid, customer.subscription.updated) to the local DB. Usage meters track endpoint calls per user and enforce plan limits.

**Deep:**
- `POST /api/billing/create-portal` → Stripe Customer Portal session.
- `POST /api/billing/create-checkout` → Stripe Checkout session with price ID.
- Webhook handler verifies `stripe-signature` header (HMAC-SHA256) before processing.
- Rate limits are enforced by a middleware that checks remaining requests from Redis, keyed by user_id + plan tier.

---

## Multi-Tenancy

### Q: How does multi-tenancy work?

**Short:** Each user belongs to an `Organization`. `OrgMembership` tracks the role. Every query is scoped by `organization_id` from the JWT. Owners can invite members via email, manage roles, delete the org, and configure SSO.

**Deep:**
- **Invitations**: Generated JWT token with expiring invite → member clicks link → joins org with default `member` role.
- **SSO/SAML**: Org stores `sso_provider` (okta/azure), `sso_metadata_url`, and `sso_entity_id`. When enabled, login redirects to IdP; SAML assertion maps attributes to `username` and `email`.

---

## Frontend

### Q: How is the frontend structured?

**Short:** React 18 SPA with Vite, React Router v6 (24 routes), AuthContext + ThemeContext, Axios API client, 16 reusable components, Tailwind CSS for styling.

**Deep:** Key architectural decisions:
- **Context over Redux**: Only two global states (auth + theme) — no need for Redux.
- **Axios interceptors**: Centralized error handling, 401 → refresh token → retry, rate limit detection → toast notification.
- **Lazy loading**: Routes are dynamically imported (`React.lazy + Suspense`) so each page bundle loads on demand.
- **ProtectedRoute/AdminRoute**: Wrapper components that check auth state before rendering children.

### Q: Explain the chat UI architecture

**Short:** The Chat page streams the conversation using a message array in state, renders via `MessageBubble` components, and shows `SourceCard` for each citation. Users can switch LLM providers from a dropdown, toggle voice I/O, and see risk flags on responses.

**Deep:** Messages are typed (`user`/`assistant`/`system`) and rendered by `<MessageBubble>` which handles markdown, source links, and code blocks. `<SourceCard>` under each response shows the document name, chunk excerpt, and similarity score. The whole conversation can be cleared with a single button.

---

## Testing

### Q: How is the application tested?

**Short:** 14 backend test files (pytest), 4 frontend test files (vitest), 7 E2E scenarios (Playwright). CI runs all tests on every push via GitHub Actions.

**Deep:**
- **Backend**: Tests cover auth (register, login, refresh, 2FA), chat RAG pipeline, document upload, clause extraction, agent tool execution, and billing webhooks. Uses a test PostgreSQL database with fixtures.
- **Frontend**: Component unit tests for Navbar, MessageBubble, Footer, ProtectedRoute — rendered with `@testing-library/react`.
- **E2E**: Real browser tests for register → login → upload → chat → extract clauses flow.

---

## Deployment

### Q: How is the application deployed?

**Short:** Docker Compose for dev, CI/CD via GitHub Actions. Production can run on any VPS with Docker or on Render/Railway. The frontend builds to static files, the backend runs as a Uvicorn/Gunicorn process.

**Deep:** The CI pipeline (`ci.yml`) has 5 parallel jobs: ruff lint, pytest (with PostgreSQL service), eslint, vitest, and Docker build. All must pass before merge.

---

## Comparison & Trade-offs

### Q: Why not use LangChain's built-in agent?

**Short:** LangChain's agent abstractions change rapidly between versions. We built a lighter, custom ReAct loop that directly controls the prompt format and tool schemas — easier to debug and maintain long-term.

### Q: What would you do differently if you started today?

1. **Use streaming from day one** — The biggest UX gap is waiting for full LLM responses.
2. **Add OCR support** — Scanned PDFs are common in legal practice; we assumed text-based PDFs.
3. **Framework-agnostic chunking** — We coupled chunking to LangChain `RecursiveCharacterTextSplitter`; a custom splitter would be more portable.
4. **Better error handling for LLM timeouts** — Currently returns a 504; should retry with a different provider automatically.

### Q: Biggest technical challenge you overcame?

**Migrating from ChromaDB to pgvector mid-project.** All existing document embeddings had to be re-embedded into the new format, the retrieval pipeline had to be rewritten from ChromaDB's collection-based API to SQLAlchemy vector similarity queries, and we had to ensure zero data loss during the cutover. We wrote a migration script that chunked the re-embedding in batches and ran a side-by-side accuracy comparison (hit rate@5) to confirm pgvector matched or exceeded ChromaDB before switching traffic.

---

## Quick-Fire Questions

| Question | Expected Answer |
|----------|----------------|
| What Python async framework? | FastAPI |
| ORM used? | SQLAlchemy 2.0 (async) |
| Vector extension? | pgvector |
| Embedding dimension? | 384 (all-MiniLM-L6-v2) |
| Default LLM provider? | Groq (Llama 3) |
| Token expiry? | Access: 30 min, Refresh: 7 days |
| Password hashing? | bcrypt |
| 2FA type? | TOTP (Time-based One-Time Password) |
| Rate limiting backend? | Redis (via slowapi) |
| Payment processor? | Stripe |
| Number of database tables? | 20 |
| Number of frontend routes? | 24 |
| Number of backend test files? | 14 |
| Number of reusable components? | 16 |
| CI runner? | GitHub Actions |
| Containerization? | Docker + Docker Compose |
| Chunk size? | 500 characters, 100 overlap |
| Similarity metric? | Cosine similarity |
| Frontend port (dev)? | 5173 |
| Backend port (dev)? | 8000 |

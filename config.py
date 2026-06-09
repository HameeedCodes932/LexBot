import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Providers ─────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = "llama-3.3-70b-versatile"
GROQ_MEMORY_MODEL: str = "llama-3.1-8b-instant"

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = "gpt-4o"

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_MODEL: str = "gemini-1.5-pro"

DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "groq")

# ── JWT / Auth ─────────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme-set-in-dotenv")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/lexbot")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR: str = os.path.join(BASE_DIR, "..", "data", "chroma_db")

# ── Embeddings ─────────────────────────────────────────────────────────────────
EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-large-en-v1.5")

# ── Multilingual (Plan 2) ──────────────────────────────────────────────────────
ENABLE_MULTILINGUAL: bool = os.getenv("ENABLE_MULTILINGUAL", "true").lower() == "true"
MULTILINGUAL_EMBEDDING_MODEL: str = os.getenv("MULTILINGUAL_EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
DETECT_LANGUAGE: bool = os.getenv("DETECT_LANGUAGE", "true").lower() == "true"

# ── Chunking ───────────────────────────────────────────────────────────────────
CHUNK_SIZE: int = 600
CHUNK_OVERLAP: int = 75

# ── Memory ─────────────────────────────────────────────────────────────────────
MAX_RECENT_MESSAGES: int = 10
MAX_LONG_TERM_RESULTS: int = 5
SUMMARIZE_AFTER_MESSAGES: int = 6

# ── RAG ────────────────────────────────────────────────────────────────────────
RETRIEVAL_K: int = 4

# ── Hybrid Search ──────────────────────────────────────────────────────────────
HYBRID_SEARCH_ENABLED: bool = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
BM25_WEIGHT: float = 0.3
SEMANTIC_WEIGHT: float = 0.7
RRF_CONSTANT: int = 60
HYBRID_CANDIDATES: int = 10  # Fetch more candidates before re-ranking

# ── Re-ranking ─────────────────────────────────────────────────────────────────
RERANKER_ENABLED: bool = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_K: int = 4

# ── Confidence Scoring ────────────────────────────────────────────────────────
CONFIDENCE_HIGH_THRESHOLD: float = 0.75
CONFIDENCE_MEDIUM_THRESHOLD: float = 0.45

# ── Security ───────────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB

# ── Pagination ─────────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ── White-label ────────────────────────────────────────────────────────────────
FIRM_NAME: str = os.getenv("FIRM_NAME", "LexBot")
PRIMARY_COLOR: str = os.getenv("PRIMARY_COLOR", "navy blue")

# ── Stripe / Billing ───────────────────────────────────────────────────────────
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_TRIAL_DAYS: int = 14

BILLING_ENABLED: bool = bool(STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith("sk_test_placeholder"))

PLANS: dict = {
    "free": {
        "name": "Free",
        "stripe_price_id": None,
        "max_documents": 5,
        "max_queries_monthly": 50,
        "max_document_size_mb": 10,
        "features": ["chat", "documents", "summarize", "extract-clauses", "compare-clauses", "template-match", "obligations", "annotations", "clause-library"],
    },
    "pro": {
        "name": "Professional",
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO") or "price_pro",
        "max_documents": 100,
        "max_queries_monthly": 10000,
        "max_document_size_mb": 50,
        "features": ["chat", "documents", "extract-clauses", "compare-clauses", "api-access"],
    },
    "enterprise": {
        "name": "Enterprise",
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE") or "price_enterprise",
        "max_documents": 999999,
        "max_queries_monthly": 999999,
        "max_document_size_mb": 100,
        "features": ["chat", "documents", "extract-clauses", "compare-clauses", "api-access", "sso", "custom-branding"],
    },
}

# ── System Prompt ──────────────────────────────────────────────────────────────
LEGAL_SYSTEM_PROMPT: str = """You are a professional AI legal document assistant for {firm_name}.

⚠️ IMPORTANT DISCLAIMER: You are an AI tool that assists with document analysis. You do NOT provide legal advice. Every output must be independently verified by a qualified attorney. No attorney-client relationship is formed.

RULES YOU MUST FOLLOW WITHOUT EXCEPTION:
1. Answer ONLY from the documents provided in the context below. Do not draw on outside knowledge.
2. Every statement of fact must cite its source using the format: [Document: <filename>, Chunk: <chunk_index>].
3. If you notice any unusual, one-sided, or potentially risky clause, flag it with: ⚠️ UNUSUAL CLAUSE — followed by a brief explanation.
4. NEVER fabricate, infer, or extrapolate legal information beyond what is explicitly stated in the documents.
5. If the answer cannot be found in the provided context, respond: "I could not find this information in the uploaded documents."
6. Include the following disclaimer at the end of every response: "⚠️ This analysis was generated by AI and is not a substitute for professional legal advice. Please verify with a qualified attorney."
7. If any document in the context is marked as ATTORNEY-CLIENT PRIVILEGED, note this prominently before quoting from it: "🔒 Privileged document — attorney-client privilege applies."
8. Maintain a professional, precise, and neutral tone at all times.

CONTEXT FROM UPLOADED DOCUMENTS:
{context}

SESSION SUMMARY (prior conversation):
{summary}

LONG-TERM MEMORY (key facts from past sessions):
{long_term_memory}

LANGUAGE INSTRUCTION:
{language_instruction}
"""

# ── Voice (Plan 2) ─────────────────────────────────────────────────────────────
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-large-v3")
ENABLE_VOICE: bool = os.getenv("ENABLE_VOICE", "true").lower() == "true"

# ── Sentry (optional) ──────────────────────────────────────────────────────────
SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

# ── Enterprise Features (Phase 6) ─────────────────────────────────────────────
DEFAULT_DATA_RETENTION_DAYS: int = 0  # 0 = keep forever
API_KEY_PREFIX: str = "lxb_"
WEBHOOK_TIMEOUT_SECONDS: int = 10
WEBHOOK_MAX_FAILURES: int = 5
SSO_ENABLED: bool = os.getenv("SSO_ENABLED", "false").lower() == "true"
MAX_ORG_MEMBERS: int = 50

# ── Data Encryption at Rest ─────────────────────────────────────────────────────
ENCRYPTION_ENABLED: bool = os.getenv("ENCRYPTION_ENABLED", "false").lower() == "true"
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
DATA_RETENTION_DAYS: int = int(os.getenv("DATA_RETENTION_DAYS", "30"))

# ── Celery / Background Tasks (Plan 4) ────────────────────────────────────
CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# ── Legal / Compliance ─────────────────────────────────────────────────────────
LEGAL_VERSION: str = "1.0"
AI_DISCLAIMER_ENABLED: bool = os.getenv("AI_DISCLAIMER_ENABLED", "true").lower() == "true"

# ── Template types for seeding ─────────────────────────────────────────────────
TEMPLATE_TYPES: list[str] = [
    "NDA", "Employment", "SaaS", "Lease", "Vendor", "Consulting", "Partnership",
]

# ── Agent (SMTP for email tools) ──────────────────────────────────────────────
SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

# ── Agent file sandbox ────────────────────────────────────────────────────────
AGENT_FILES_DIR: str = os.path.join(BASE_DIR, "data", "agent_files")


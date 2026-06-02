import json
import logging
import os
import uuid
import io
from contextlib import asynccontextmanager
from typing import Optional

import sentry_sdk
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

import config
from datetime import datetime, timezone

from database import init_db, get_session, Document, User, Invoice, ContractTemplate, Obligation, SavedClause, FeatureUsage, WebhookEndpoint, APIKey, Organization, OrgMembership
from auth import (
    UserRegister,
    UserLogin,
    Token,
    create_user,
    get_user_by_email,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
    promote_user_to_admin,
    require_org_member,
    require_org_admin,
)
from ingestion import ingestion_service
from rag_chain import rag_chain
from analytics import get_admin_stats
from memory_service import memory_service
from billing import (
    get_user_plan,
    get_monthly_usage,
    check_feature_access,
    create_checkout_session,
    create_portal_session,
    get_or_create_customer,
    handle_webhook,
)
from legal_content import (
    TERMS_OF_SERVICE,
    PRIVACY_POLICY,
    DPA,
    AI_DISCLAIMER,
    DISCLAIMER_SHORT,
    LAST_UPDATED,
)
from llm_provider import llm_provider
from search_engine import search_engine
from organization import org_service
from audit import audit_service
from webhooks import webhook_service
from retention import retention_service
from sso import sso_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

# ── Standard contract template definitions ─────────────────────────────────────
STANDARD_TEMPLATES = [
    {
        "name": "Standard NDA",
        "description": "Non-Disclosure Agreement template with essential clauses",
        "template_type": "NDA",
        "clauses": [
            {"type": "confidentiality", "description": "Definition and scope of confidential information", "required": True},
            {"type": "termination", "description": "Agreement duration and termination conditions", "required": True},
            {"type": "indemnification", "description": "Indemnification for breach of confidentiality", "required": False},
            {"type": "governing-law", "description": "Applicable governing law and jurisdiction", "required": True},
            {"type": "dispute-resolution", "description": "Mechanism for resolving disputes", "required": False},
        ],
    },
    {
        "name": "Standard Employment Agreement",
        "description": "Employment contract template with comprehensive clauses",
        "template_type": "Employment",
        "clauses": [
            {"type": "payment", "description": "Compensation, benefits, and payment terms", "required": True},
            {"type": "termination", "description": "Termination conditions and notice period", "required": True},
            {"type": "confidentiality", "description": "Employee confidentiality obligations", "required": True},
            {"type": "intellectual-property", "description": "IP ownership and assignment", "required": True},
            {"type": "indemnification", "description": "Mutual indemnification terms", "required": False},
            {"type": "liability", "description": "Limitation of liability", "required": False},
            {"type": "dispute-resolution", "description": "Dispute resolution mechanism", "required": False},
            {"type": "governing-law", "description": "Governing law clause", "required": True},
        ],
    },
    {
        "name": "Standard SaaS Agreement",
        "description": "Software-as-a-Service subscription agreement",
        "template_type": "SaaS",
        "clauses": [
            {"type": "payment", "description": "Subscription fees, billing, and payment terms", "required": True},
            {"type": "termination", "description": "Subscription termination and cancellation", "required": True},
            {"type": "liability", "description": "Limitation of liability and warranty disclaimers", "required": True},
            {"type": "warranty", "description": "Service level guarantees and warranties", "required": True},
            {"type": "confidentiality", "description": "Data protection and confidentiality", "required": True},
            {"type": "intellectual-property", "description": "IP ownership and license grants", "required": True},
            {"type": "indemnification", "description": "Mutual indemnification provisions", "required": True},
            {"type": "force-majeure", "description": "Force majeure events and relief", "required": False},
            {"type": "governing-law", "description": "Governing law and jurisdiction", "required": True},
            {"type": "dispute-resolution", "description": "Arbitration or litigation clause", "required": False},
        ],
    },
    {
        "name": "Standard Vendor Agreement",
        "description": "Vendor/supplier services contract",
        "template_type": "Vendor",
        "clauses": [
            {"type": "payment", "description": "Payment terms and conditions", "required": True},
            {"type": "termination", "description": "Contract termination rights", "required": True},
            {"type": "warranty", "description": "Vendor warranties and representations", "required": True},
            {"type": "liability", "description": "Liability caps and exclusions", "required": True},
            {"type": "indemnification", "description": "Vendor indemnification obligations", "required": True},
            {"type": "confidentiality", "description": "Information confidentiality", "required": True},
            {"type": "governing-law", "description": "Applicable law", "required": True},
        ],
    },
]


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.SENTRY_DSN:
        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            traces_sample_rate=0.25,
            profiles_sample_rate=0.10,
            environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        )
        logger.info("Sentry initialized.")
    await init_db()
    _ = ingestion_service.embeddings
    # Seed contract templates
    await _seed_templates()
    
    # Run data retention policies
    try:
        from retention import retention_service
        from database import async_session_factory
        async with async_session_factory() as session:
            await retention_service.apply_all_retention_policies(session)
            logger.info("Data retention policies applied on startup.")
    except Exception as exc:
        logger.warning(f"Failed to apply retention policies on startup: {exc}")

    logger.info("LexBot 3.0 ready — Phase 6 Enterprise Features active.")
    yield


async def _seed_templates():
    """Seed standard contract templates if none exist."""
    from database import async_session_factory
    async with async_session_factory() as session:
        try:
            count = await session.scalar(select(func.count(ContractTemplate.id)))
            if count and count > 0:
                return
            for tmpl in STANDARD_TEMPLATES:
                t = ContractTemplate(
                    name=tmpl["name"],
                    description=tmpl["description"],
                    template_type=tmpl["template_type"],
                    clauses_json=json.dumps(tmpl["clauses"]),
                )
                session.add(t)
            await session.commit()
            logger.info("Seeded %d contract templates.", len(STANDARD_TEMPLATES))
        except Exception as exc:
            await session.rollback()
            logger.warning("Template seeding failed: %s", exc)


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="LexBot 2.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if request.headers.get("x-forwarded-proto") == "http":
        url = request.url.replace(scheme="https")
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url)
    return await call_next(request)


# ── Request / Response models ──────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    provider: Optional[str] = None
    document_filter: Optional[list[str]] = None


class ClauseExtractRequest(BaseModel):
    document_name: str
    clause_type: str


class CompareClausesRequest(BaseModel):
    document_one: str
    document_two: str
    clause_type: str


class SummarizeRequest(BaseModel):
    document_name: str
    summary_type: str = "detailed"  # brief | detailed | executive


class ObligationExtractRequest(BaseModel):
    document_name: str


class ObligationStatusUpdate(BaseModel):
    status: str  # pending | completed | overdue


class TemplateMatchRequest(BaseModel):
    document_name: str
    template_id: int


class SaveClauseRequest(BaseModel):
    clause_type: str
    title: str = ""
    content: str
    source_document: str = ""
    notes: str = ""


class TableExtractRequest(BaseModel):
    document_name: str


class BillingPortalRequest(BaseModel):
    origin: str


# ── Phase 2 constants ──────────────────────────────────────────────────────────
VALID_CLAUSE_TYPES = [
    "indemnification", "termination", "payment", "liability",
    "confidentiality", "governing-law", "dispute-resolution",
    "warranty", "intellectual-property", "force-majeure",
]

CLAUSE_QUERIES = {
    "indemnification": "indemnification clause indemnify hold harmless indemnity",
    "termination": "termination clause termination of agreement terminate this contract",
    "payment": "payment clause payment terms fees compensation",
    "liability": "liability clause limitation of liability damages",
    "confidentiality": "confidentiality clause confidential information nondisclosure",
    "governing-law": "governing law clause choice of law jurisdiction applicable law",
    "dispute-resolution": "dispute resolution clause arbitration mediation disputes",
    "warranty": "warranty clause warranties representations guarantee",
    "intellectual-property": "intellectual property clause IP ownership license",
    "force-majeure": "force majeure clause unforeseeable events act of god",
}


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/register")
@limiter.limit("5/minute")
async def register(request: Request, body: UserRegister, session: AsyncSession = Depends(get_session)):
    result = await create_user(session=session, username=body.username, email=body.email, password=body.password, firm_name=body.firm_name)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    logger.info("New user registered: %s", body.email)
    return {"message": "Registration successful. You may now log in."}


@app.post("/api/auth/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin, session: AsyncSession = Depends(get_session)):
    user = await get_user_by_email(session, body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Contact your administrator.")
    token = create_access_token({"sub": str(user["id"])})
    safe_user = {k: v for k, v in user.items() if k != "hashed_password"}
    return Token(access_token=token, token_type="bearer", user=safe_user)


@app.get("/api/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {k: v for k, v in current_user.items() if k != "hashed_password"}


# ══════════════════════════════════════════════════════════════════════════════
#  PROVIDERS ENDPOINT (Phase 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/providers")
async def list_providers(current_user: dict = Depends(get_current_user)):
    """List available LLM providers."""
    return llm_provider.get_available_providers()


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/chat")
async def chat(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    access = await check_feature_access(session, current_user["id"], "chat")
    if not access["allowed"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={
            "code": access["reason"],
            "message": "Monthly query limit reached. Upgrade your plan to continue.",
            "plan": access["plan"],
            "usage": access["usage"],
        })
    session_id = body.session_id or str(uuid.uuid4())
    org_id = current_user.get("org_id")
    
    result = await rag_chain.query(
        question=body.question,
        user_id=current_user["id"],
        session_id=session_id,
        provider=body.provider,
        document_filter=body.document_filter,
        org_id=org_id,
    )

    # Audit logging
    from audit import audit_service
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="query.ask",
        resource_type="session",
        resource_id=session_id,
        details={"question": body.question, "provider": body.provider, "confidence": result.get("confidence", {}).get("score")},
    )

    # Webhook triggering
    if org_id:
        from webhooks import webhook_service
        await webhook_service.trigger(
            org_id=org_id,
            event_type="query.completed",
            data={
                "session_id": session_id,
                "user_id": current_user["id"],
                "question": body.question,
                "confidence_score": result.get("confidence", {}).get("score"),
            }
        )

    result["disclaimer"] = DISCLAIMER_SHORT if config.AI_DISCLAIMER_ENABLED else None
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD / DOCUMENTS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    visibility: Optional[str] = Query("personal"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if visibility not in ("personal", "org"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visibility must be 'personal' or 'org'")

    if visibility == "org" and not current_user.get("org_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must belong to an organization to upload shared documents")

    access = await check_feature_access(session, current_user["id"], "documents")
    if not access["allowed"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={
            "code": access["reason"],
            "message": "Document limit reached. Upgrade your plan to upload more documents.",
            "plan": access["plan"],
            "usage": access["usage"],
        })
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type '{ext}'. Allowed: txt, pdf, docx.")

    org_id = current_user.get("org_id")
    exists = await ingestion_service.check_document_exists(session, current_user["id"], file.filename, org_id=org_id)
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Document '{file.filename}' already uploaded. Delete it first or rename the file.")

    contents = await file.read()
    if len(contents) > config.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File size exceeds {config.MAX_UPLOAD_SIZE // (1024*1024)}MB limit.")

    text = ""
    ocr_used = False

    try:
        if ext == "txt":
            text = contents.decode("utf-8", errors="ignore")

        elif ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(contents))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

            # OCR fallback for scanned PDFs
            if not text.strip():
                try:
                    from pdf2image import convert_from_bytes
                    import pytesseract
                    images = convert_from_bytes(contents)
                    ocr_parts = []
                    for img in images:
                        ocr_text = pytesseract.image_to_string(img)
                        if ocr_text.strip():
                            ocr_parts.append(ocr_text)
                    if ocr_parts:
                        text = "\n".join(ocr_parts)
                        ocr_used = True
                        logger.info("OCR fallback used for '%s': %d pages", file.filename, len(images))
                except ImportError:
                    logger.warning("OCR libraries not available (pytesseract/pdf2image). Scanned PDF cannot be processed.")
                except Exception as ocr_exc:
                    logger.warning("OCR failed for '%s': %s", file.filename, ocr_exc)

        elif ext == "docx":
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(contents))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to extract text: {str(exc)}")

    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No extractable text found in the uploaded document.")

    result = await ingestion_service.ingest_text(
        text=text, filename=file.filename, user_id=current_user["id"], org_id=org_id, visibility=visibility
    )

    # Invalidate BM25 cache for user/org
    search_engine.invalidate_bm25_cache(current_user["id"], org_id)

    result["ocr_used"] = ocr_used

    # Audit logging
    from audit import audit_service
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="document.upload",
        resource_type="document",
        resource_id=file.filename,
        details={"visibility": visibility, "ocr_used": ocr_used}
    )

    # Webhook triggering
    if org_id:
        from webhooks import webhook_service
        await webhook_service.trigger(
            org_id=org_id,
            event_type="document.uploaded",
            data={
                "filename": file.filename,
                "user": current_user["email"],
                "visibility": visibility,
            }
        )

    return result


@app.get("/api/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(config.DEFAULT_PAGE_SIZE, ge=1, le=config.MAX_PAGE_SIZE),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await ingestion_service.get_user_documents(
        session, current_user["id"], org_id=current_user.get("org_id"), page=page, page_size=page_size
    )


@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    is_org_admin = current_user.get("org_role") in ("owner", "admin")
    org_id = current_user.get("org_id")
    deleted = await ingestion_service.delete_document(
        current_user["id"], document_id, org_id=org_id, is_org_admin=is_org_admin
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or unauthorized.")
    
    # Audit logging
    from audit import audit_service
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="document.delete",
        resource_type="document",
        resource_id=str(document_id)
    )

    # Webhook triggering
    if org_id:
        from webhooks import webhook_service
        await webhook_service.trigger(
            org_id=org_id,
            event_type="document.deleted",
            data={
                "document_id": document_id,
                "user_id": current_user["id"],
            }
        )

    search_engine.invalidate_bm25_cache(current_user["id"], org_id)
    return {"message": f"Document {document_id} deleted."}


# ══════════════════════════════════════════════════════════════════════════════
#  MEMORY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/memory/{session_id}")
async def get_memory(session_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    user_id = current_user["id"]
    return {
        "recent_messages": await memory_service.loadRecentMessages(session, user_id, session_id),
        "summary": await memory_service.loadSummary(session, user_id, session_id),
        "long_term_memory": await memory_service.searchLongTermMemory(session, user_id, ""),
    }


@app.delete("/api/memory/{session_id}")
async def clear_memory(session_id: str, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await memory_service.clearSessionMemory(session, current_user["id"], session_id)
    return {"message": f"Memory cleared for session '{session_id}'."}


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/analytics")
async def admin_analytics(admin: dict = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return await get_admin_stats(session)


@app.get("/api/admin/users")
async def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(config.DEFAULT_PAGE_SIZE, ge=1, le=config.MAX_PAGE_SIZE),
    admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    offset = (page - 1) * page_size
    total = await session.scalar(select(func.count(User.id)))
    result = await session.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size))
    rows = result.scalars().all()
    items = [
        {k: v for k, v in {
            "id": r.id, "username": r.username, "email": r.email, "role": r.role,
            "firm_name": r.firm_name, "is_active": r.is_active,
            "created_at": str(r.created_at) if r.created_at else None,
        }.items() if k != "hashed_password"} for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": -(-total // page_size) if total else 0}


@app.patch("/api/admin/users/{user_id}/deactivate")
async def admin_deactivate_user(user_id: int, admin: dict = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    await session.execute(update(User).where(User.id == user_id).values(is_active=False))
    logger.info("User deactivated: user_id=%d by admin=%d", user_id, admin["id"])
    return {"message": f"User {user_id} has been deactivated."}


@app.post("/api/admin/users/{user_id}/promote")
async def admin_promote_user(user_id: int, admin: dict = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    result = await promote_user_to_admin(session, user_id)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    logger.info("User promoted to admin: user_id=%d by admin=%d", user_id, admin["id"])
    return {"message": result["message"]}


# ══════════════════════════════════════════════════════════════════════════════
#  CLAUSE EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/extract-clauses")
async def extract_clauses(
    body: ClauseExtractRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    access = await check_feature_access(session, current_user["id"], "extract-clauses")
    if not access["allowed"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={
            "code": access["reason"],
            "message": "Upgrade your plan to use clause extraction.",
            "plan": access["plan"],
            "usage": access["usage"],
        })
    try:
        if body.clause_type not in VALID_CLAUSE_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid clause type '{body.clause_type}'. Valid options: {', '.join(VALID_CLAUSE_TYPES)}")

        if not body.document_name.strip() or ".." in body.document_name or "/" in body.document_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document name.")

        user_id = current_user["id"]
        doc_row = await session.execute(select(Document.id).where(Document.user_id == user_id, Document.filename == body.document_name))
        if not doc_row.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{body.document_name}' not found.")

        collection = ingestion_service.get_collection(user_id)
        query_text = CLAUSE_QUERIES.get(body.clause_type, body.clause_type)
        chunks = rag_chain._search_document(collection, query_text, body.document_name, k=20)

        fu = FeatureUsage(user_id=user_id, feature_name="extract-clauses", clause_type=body.clause_type)
        session.add(fu)

        if not chunks:
            return {"document_name": body.document_name, "clause_type": body.clause_type, "total_clauses_found": 0, "results": [], "message": f"No {body.clause_type} clauses found in '{body.document_name}'."}

        llm = llm_provider.get_llm(temperature=0)
        results = []
        for doc in chunks:
            meta = doc.metadata or {}
            chunk_text = doc.page_content
            prompt = f"Does the following chunk contain a {body.clause_type} clause? If yes, extract and summarize it in 2-3 sentences. If no, respond with exactly: NONE\n\nChunk:\n{chunk_text}"
            try:
                resp = await llm.ainvoke([HumanMessage(content=prompt)])
                summary = resp.content.strip()
                if summary.upper() != "NONE":
                    results.append({"chunk_index": meta.get("chunk_index", 0), "summary": summary, "raw_text": chunk_text})
                    if len(results) >= 10:
                        break
            except Exception:
                continue

        return {"document_name": body.document_name, "clause_type": body.clause_type, "total_clauses_found": len(results), "results": results}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is temporarily unavailable. Please try again later.")


# ══════════════════════════════════════════════════════════════════════════════
#  CONTRACT COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/compare-clauses")
async def compare_clauses(
    body: CompareClausesRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    access = await check_feature_access(session, current_user["id"], "compare-clauses")
    if not access["allowed"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={
            "code": access["reason"],
            "message": "Upgrade your plan to use contract comparison.",
            "plan": access["plan"],
            "usage": access["usage"],
        })
    try:
        if body.clause_type not in VALID_CLAUSE_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid clause type '{body.clause_type}'.")

        for name in (body.document_one, body.document_two):
            if not name.strip() or ".." in name or "/" in name:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid document name: '{name}'.")

        if body.document_one == body.document_two:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="document_one and document_two must be different files.")

        user_id = current_user["id"]
        doc1 = await session.execute(select(Document.id).where(Document.user_id == user_id, Document.filename == body.document_one))
        doc2 = await session.execute(select(Document.id).where(Document.user_id == user_id, Document.filename == body.document_two))

        missing = []
        if not doc1.scalar_one_or_none():
            missing.append(f"'{body.document_one}'")
        if not doc2.scalar_one_or_none():
            missing.append(f"'{body.document_two}'")
        if missing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document(s) not found: {', '.join(missing)}.")

        collection = ingestion_service.get_collection(user_id)
        query_text = CLAUSE_QUERIES.get(body.clause_type, body.clause_type)
        chunks_one = rag_chain._search_document(collection, query_text, body.document_one, k=3)
        chunks_two = rag_chain._search_document(collection, query_text, body.document_two, k=3)

        if not chunks_one:
            return {"document_one": body.document_one, "document_two": body.document_two, "clause_type": body.clause_type, "comparison": None, "sources_document_one": [], "sources_document_two": [d.metadata.get("chunk_index", 0) for d in chunks_two] if chunks_two else [], "message": f"No {body.clause_type} clauses found in '{body.document_one}'."}

        if not chunks_two:
            return {"document_one": body.document_one, "document_two": body.document_two, "clause_type": body.clause_type, "comparison": None, "sources_document_one": [d.metadata.get("chunk_index", 0) for d in chunks_one], "sources_document_two": [], "message": f"No {body.clause_type} clauses found in '{body.document_two}'."}

        def format_chunks(chunks, doc_name):
            parts = []
            for d in chunks:
                meta = d.metadata or {}
                idx = meta.get("chunk_index", "?")
                parts.append(f"[Chunk {idx}]\n{d.page_content}")
            return f"--- {doc_name} ---\n" + "\n\n".join(parts)

        text_one = format_chunks(chunks_one, body.document_one)
        text_two = format_chunks(chunks_two, body.document_two)

        llm = llm_provider.get_llm(temperature=0)
        prompt = f"You are a legal document analyst.\n\nHere are {body.clause_type} clauses from two contracts.\n\n{text_one}\n\n{text_two}\n\nProduce a structured comparison with these sections:\nKey Similarities\nKey Differences\nWhich is more favorable to the client and why\nRed flags if any"
        try:
            resp = await llm.ainvoke([HumanMessage(content=prompt)], max_tokens=1024)
            comparison = resp.content.strip()
        except Exception:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is temporarily unavailable.")

        fu = FeatureUsage(user_id=user_id, feature_name="compare-clauses", clause_type=body.clause_type)
        session.add(fu)

        return {
            "document_one": body.document_one, "document_two": body.document_two, "clause_type": body.clause_type,
            "comparison": comparison,
            "sources_document_one": [d.metadata.get("chunk_index", 0) for d in chunks_one],
            "sources_document_two": [d.metadata.get("chunk_index", 0) for d in chunks_two],
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is temporarily unavailable.")


# ══════════════════════════════════════════════════════════════════════════════
#  CONTRACT SUMMARIZATION (Phase 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/summarize")
async def summarize_document(body: SummarizeRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    access = await check_feature_access(session, current_user["id"], "summarize")
    if not access["allowed"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={
            "code": access["reason"],
            "message": "Upgrade your plan to use document summarization.",
            "plan": access["plan"],
            "usage": access["usage"],
        })
    try:
        user_id = current_user["id"]
        doc_row = await session.execute(select(Document.id).where(Document.user_id == user_id, Document.filename == body.document_name))
        if not doc_row.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{body.document_name}' not found.")

        # Get all chunks for this document
        collection = ingestion_service.get_collection(user_id)
        all_chunks = collection.similarity_search("", k=200, filter={"source": body.document_name})

        if not all_chunks:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No document content found in the index.")

        # Sort by chunk_index
        all_chunks.sort(key=lambda d: d.metadata.get("chunk_index", 0))

        llm = llm_provider.get_llm(temperature=0)

        # Map phase: summarize each chunk
        chunk_summaries = []
        for chunk in all_chunks[:30]:  # Limit to 30 chunks
            map_prompt = f"Summarize the following legal document excerpt in 2-3 sentences, focusing on key terms, parties, obligations, and dates:\n\n{chunk.page_content}"
            try:
                resp = await llm.ainvoke([HumanMessage(content=map_prompt)])
                chunk_summaries.append(resp.content.strip())
            except Exception:
                continue

        if not chunk_summaries:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to analyze document content.")

        # Reduce phase: combine into structured summary
        combined = "\n\n".join(f"Section {i+1}: {s}" for i, s in enumerate(chunk_summaries))

        style_instructions = {
            "brief": "Provide a concise 3-5 sentence overview of this contract.",
            "detailed": "Provide a comprehensive summary organized into: Key Parties, Effective Date & Term, Key Obligations, Notable Provisions, Potential Risks/Red Flags.",
            "executive": "Provide an executive briefing suitable for a senior partner: start with a one-sentence bottom line, then cover deal structure, key commercial terms, material risks, and recommended actions.",
        }

        reduce_prompt = (
            f"You are a senior legal analyst. Based on the following section summaries of a contract document '{body.document_name}', "
            f"{style_instructions.get(body.summary_type, style_instructions['detailed'])}\n\n"
            f"Section Summaries:\n{combined}"
        )

        resp = await llm.ainvoke([HumanMessage(content=reduce_prompt)], max_tokens=2048)

        fu = FeatureUsage(user_id=user_id, feature_name="summarize", clause_type=body.summary_type)
        session.add(fu)

        return {
            "document_name": body.document_name,
            "summary_type": body.summary_type,
            "summary": resp.content.strip(),
            "chunks_analyzed": len(chunk_summaries),
            "total_chunks": len(all_chunks),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Summarization failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is temporarily unavailable.")


# ══════════════════════════════════════════════════════════════════════════════
#  OBLIGATION TRACKER (Phase 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/obligations/extract")
async def extract_obligations(body: ObligationExtractRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        user_id = current_user["id"]
        doc_result = await session.execute(select(Document).where(Document.user_id == user_id, Document.filename == body.document_name))
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{body.document_name}' not found.")

        # Search for obligation-related content
        collection = ingestion_service.get_collection(user_id)
        obligation_queries = [
            "obligations duties responsibilities shall must required",
            "deadlines dates timeline due by within days",
            "payment fees compensation amount",
            "delivery milestones deliverables",
        ]

        all_chunks = []
        for q in obligation_queries:
            chunks = rag_chain._search_document(collection, q, body.document_name, k=5)
            all_chunks.extend(chunks)

        # Deduplicate
        seen = set()
        unique_chunks = []
        for c in all_chunks:
            key = c.page_content[:100]
            if key not in seen:
                seen.add(key)
                unique_chunks.append(c)

        if not unique_chunks:
            return {"document_name": body.document_name, "obligations_found": 0, "obligations": [], "message": "No obligations found."}

        combined_text = "\n\n---\n\n".join(c.page_content for c in unique_chunks[:15])

        llm = llm_provider.get_llm(temperature=0)
        prompt = (
            "You are a legal obligation analyst. Extract ALL obligations, duties, and deadlines from this contract text.\n\n"
            "For each obligation, provide a JSON object with these fields:\n"
            '- "obligation_text": brief description of the obligation\n'
            '- "party_responsible": which party must fulfill it\n'
            '- "deadline": deadline or timeframe (or "Not specified")\n'
            '- "obligation_type": one of "payment", "delivery", "reporting", "compliance", "other"\n\n'
            "Respond with a JSON array only. No explanation.\n\n"
            f"Contract text:\n{combined_text}"
        )

        resp = await llm.ainvoke([HumanMessage(content=prompt)], max_tokens=2048)

        # Parse LLM response
        obligations_data = []
        try:
            raw = resp.content.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            obligations_data = json.loads(raw)
            if not isinstance(obligations_data, list):
                obligations_data = [obligations_data]
        except (json.JSONDecodeError, Exception):
            logger.warning("Failed to parse obligation JSON from LLM response")
            obligations_data = []

        # Save to database
        saved = []
        for ob in obligations_data[:20]:  # Limit to 20
            o = Obligation(
                user_id=user_id,
                document_id=doc.id,
                obligation_text=ob.get("obligation_text", ""),
                party_responsible=ob.get("party_responsible", ""),
                deadline=ob.get("deadline", "Not specified"),
                obligation_type=ob.get("obligation_type", "other"),
                status="pending",
                source_document=body.document_name,
            )
            session.add(o)
            saved.append(ob)

        fu = FeatureUsage(user_id=user_id, feature_name="extract-obligations", clause_type=None)
        session.add(fu)

        return {"document_name": body.document_name, "obligations_found": len(saved), "obligations": saved}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Obligation extraction failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is temporarily unavailable.")


@app.get("/api/obligations")
async def list_obligations(
    status_filter: Optional[str] = Query(None),
    obligation_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(Obligation).where(Obligation.user_id == current_user["id"])
    if status_filter:
        query = query.where(Obligation.status == status_filter)
    if obligation_type:
        query = query.where(Obligation.obligation_type == obligation_type)
    query = query.order_by(Obligation.created_at.desc())

    result = await session.execute(query)
    rows = result.scalars().all()
    return [
        {
            "id": r.id, "obligation_text": r.obligation_text,
            "party_responsible": r.party_responsible, "deadline": r.deadline,
            "obligation_type": r.obligation_type, "status": r.status,
            "source_document": r.source_document,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]


@app.patch("/api/obligations/{obligation_id}/status")
async def update_obligation_status(
    obligation_id: int,
    body: ObligationStatusUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if body.status not in ("pending", "completed", "overdue"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status must be: pending, completed, or overdue.")

    result = await session.execute(select(Obligation).where(Obligation.id == obligation_id, Obligation.user_id == current_user["id"]))
    ob = result.scalar_one_or_none()
    if not ob:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obligation not found.")

    await session.execute(update(Obligation).where(Obligation.id == obligation_id).values(status=body.status))
    return {"message": f"Obligation {obligation_id} status updated to '{body.status}'."}


@app.delete("/api/obligations/{obligation_id}")
async def delete_obligation(obligation_id: int, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Obligation).where(Obligation.id == obligation_id, Obligation.user_id == current_user["id"]))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obligation not found.")
    await session.execute(delete(Obligation).where(Obligation.id == obligation_id))
    return {"message": f"Obligation {obligation_id} deleted."}


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE MATCHING (Phase 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/templates")
async def list_templates(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ContractTemplate).order_by(ContractTemplate.name))
    rows = result.scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "description": r.description,
            "template_type": r.template_type,
            "clauses": json.loads(r.clauses_json) if r.clauses_json else [],
        }
        for r in rows
    ]


@app.post("/api/templates/match")
async def match_template(body: TemplateMatchRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        user_id = current_user["id"]

        # Verify document
        doc_row = await session.execute(select(Document.id).where(Document.user_id == user_id, Document.filename == body.document_name))
        if not doc_row.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{body.document_name}' not found.")

        # Get template
        tmpl_row = await session.execute(select(ContractTemplate).where(ContractTemplate.id == body.template_id))
        template = tmpl_row.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

        expected_clauses = json.loads(template.clauses_json) if template.clauses_json else []
        if not expected_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template has no clauses defined.")

        # Check each expected clause type
        collection = ingestion_service.get_collection(user_id)
        clause_results = []
        found_count = 0

        llm = llm_provider.get_llm(temperature=0)

        for clause in expected_clauses:
            ct = clause["type"]
            query_text = CLAUSE_QUERIES.get(ct, ct)
            chunks = rag_chain._search_document(collection, query_text, body.document_name, k=3)

            found = False
            summary = ""

            if chunks:
                # Verify with LLM
                chunk_text = chunks[0].page_content
                verify_prompt = f"Does this text contain a {ct} clause? Answer YES or NO, then briefly summarize if YES.\n\nText:\n{chunk_text}"
                try:
                    resp = await llm.ainvoke([HumanMessage(content=verify_prompt)])
                    content = resp.content.strip()
                    if content.upper().startswith("YES"):
                        found = True
                        summary = content[3:].strip().lstrip(".,:-").strip()
                        found_count += 1
                except Exception:
                    pass

            clause_results.append({
                "clause_type": ct,
                "description": clause.get("description", ""),
                "required": clause.get("required", False),
                "found": found,
                "summary": summary,
                "status": "present" if found else ("missing_required" if clause.get("required") else "missing_optional"),
            })

        total = len(expected_clauses)
        required_count = sum(1 for c in expected_clauses if c.get("required"))
        required_found = sum(1 for cr in clause_results if cr["found"] and cr["required"])
        compliance_score = round((found_count / total) * 100) if total else 0

        fu = FeatureUsage(user_id=user_id, feature_name="template-match", clause_type=template.template_type)
        session.add(fu)

        return {
            "document_name": body.document_name,
            "template_name": template.name,
            "template_type": template.template_type,
            "compliance_score": compliance_score,
            "total_clauses": total,
            "found_clauses": found_count,
            "required_total": required_count,
            "required_found": required_found,
            "clause_results": clause_results,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Template matching failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is temporarily unavailable.")


# ══════════════════════════════════════════════════════════════════════════════
#  TABLE EXTRACTION (Phase 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/extract-tables")
async def extract_tables(body: TableExtractRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        user_id = current_user["id"]
        doc_row = await session.execute(select(Document.id).where(Document.user_id == user_id, Document.filename == body.document_name))
        if not doc_row.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{body.document_name}' not found.")

        collection = ingestion_service.get_collection(user_id)
        table_queries = [
            "table schedule matrix list amount fee percentage",
            "payment schedule rates pricing tier",
            "timeline milestones deliverables deadlines",
        ]

        all_chunks = []
        seen = set()
        for q in table_queries:
            chunks = rag_chain._search_document(collection, q, body.document_name, k=5)
            for c in chunks:
                key = c.page_content[:100]
                if key not in seen:
                    seen.add(key)
                    all_chunks.append(c)

        if not all_chunks:
            return {"document_name": body.document_name, "tables_found": 0, "tables": [], "message": "No tabular data found."}

        combined = "\n\n---\n\n".join(c.page_content for c in all_chunks[:10])

        llm = llm_provider.get_llm(temperature=0)
        prompt = (
            "You are a data extraction specialist. Find ALL tabular/structured data in this contract text.\n\n"
            "For each table found, provide a JSON object with:\n"
            '- "title": descriptive title for the table\n'
            '- "headers": array of column header strings\n'
            '- "rows": array of arrays (each inner array is one row of values)\n\n'
            "Respond with a JSON array of table objects. If no tables found, respond with [].\n\n"
            f"Contract text:\n{combined}"
        )

        resp = await llm.ainvoke([HumanMessage(content=prompt)], max_tokens=2048)

        tables = []
        try:
            raw = resp.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            tables = json.loads(raw)
            if not isinstance(tables, list):
                tables = [tables]
        except (json.JSONDecodeError, Exception):
            tables = []

        fu = FeatureUsage(user_id=user_id, feature_name="extract-tables", clause_type=None)
        session.add(fu)

        return {"document_name": body.document_name, "tables_found": len(tables), "tables": tables}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Table extraction failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is temporarily unavailable.")


# ══════════════════════════════════════════════════════════════════════════════
#  CLAUSE LIBRARY (Phase 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/clauses/save")
async def save_clause(body: SaveClauseRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    clause = SavedClause(
        user_id=current_user["id"],
        clause_type=body.clause_type,
        title=body.title or f"{body.clause_type} clause",
        content=body.content,
        source_document=body.source_document,
        notes=body.notes,
    )
    session.add(clause)
    await session.flush()
    return {"id": clause.id, "message": "Clause saved to library."}


@app.get("/api/clauses")
async def list_clauses(
    clause_type: Optional[str] = Query(None),
    benchmarks_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(SavedClause).where(SavedClause.user_id == current_user["id"])
    if clause_type:
        query = query.where(SavedClause.clause_type == clause_type)
    if benchmarks_only:
        query = query.where(SavedClause.is_benchmark)
    query = query.order_by(SavedClause.created_at.desc())

    result = await session.execute(query)
    rows = result.scalars().all()
    return [
        {
            "id": r.id, "clause_type": r.clause_type, "title": r.title,
            "content": r.content, "source_document": r.source_document,
            "notes": r.notes, "is_benchmark": r.is_benchmark,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]


@app.delete("/api/clauses/{clause_id}")
async def delete_clause(clause_id: int, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(SavedClause).where(SavedClause.id == clause_id, SavedClause.user_id == current_user["id"]))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clause not found.")
    await session.execute(delete(SavedClause).where(SavedClause.id == clause_id))
    return {"message": "Clause deleted."}


@app.patch("/api/clauses/{clause_id}/benchmark")
async def toggle_benchmark(clause_id: int, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(SavedClause).where(SavedClause.id == clause_id, SavedClause.user_id == current_user["id"]))
    clause = result.scalar_one_or_none()
    if not clause:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clause not found.")
    new_value = not clause.is_benchmark
    await session.execute(update(SavedClause).where(SavedClause.id == clause_id).values(is_benchmark=new_value))
    return {"id": clause_id, "is_benchmark": new_value, "message": f"Clause {'marked' if new_value else 'unmarked'} as benchmark."}


# ══════════════════════════════════════════════════════════════════════════════
#  BILLING / SUBSCRIPTION (Phase 5)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/billing/webhook")
async def billing_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    return await handle_webhook(payload, sig)


@app.post("/api/billing/create-checkout")
async def billing_create_checkout(
    body: BillingPortalRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    price_id = config.PLANS["pro"]["stripe_price_id"]
    await get_or_create_customer(session, current_user)
    url = await create_checkout_session(current_user["id"], price_id, body.origin)
    return {"url": url}


@app.post("/api/billing/portal")
async def billing_portal(
    body: BillingPortalRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    customer_id = current_user.get("stripe_customer_id") or "cus_demo"
    url = await create_portal_session(current_user["id"], customer_id, body.origin)
    return {"url": url}


@app.get("/api/billing/subscription")
async def billing_subscription(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    plan = await get_user_plan(session, current_user["id"])
    usage = await get_monthly_usage(session, current_user["id"])
    return {
        "plan": plan,
        "usage": usage,
        "customer_id": current_user.get("stripe_customer_id"),
    }


@app.get("/api/billing/invoices")
async def billing_invoices(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Invoice)
        .where(Invoice.user_id == current_user["id"])
        .order_by(Invoice.created_at.desc())
        .limit(20)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "amount_paid": r.amount_paid,
            "currency": r.currency,
            "status": r.status,
            "period_start": str(r.period_start) if r.period_start else None,
            "period_end": str(r.period_end) if r.period_end else None,
            "invoice_pdf": r.invoice_pdf,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]
# Mount static directory for logo / branding uploads at module level
_static_dir = os.path.join(config.BASE_DIR, "static")
os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTERPRISE & MULTI-TENANCY MODELS & ENDPOINTS (Phase 6)
# ══════════════════════════════════════════════════════════════════════════════

class CreateOrgRequest(BaseModel):
    name: str


class InviteMemberRequest(BaseModel):
    email: str
    role: str  # owner/admin/member/viewer


class UpdateMemberRoleRequest(BaseModel):
    role: str


class OrgSettingsUpdate(BaseModel):
    name: Optional[str] = None
    custom_system_prompt: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    custom_domain: Optional[str] = None
    data_retention_days: Optional[int] = None


class CreateAPIKeyRequest(BaseModel):
    name: str
    expires_in_days: Optional[int] = None
    scopes: Optional[list[str]] = None


class CreateWebhookRequest(BaseModel):
    url: str
    events: list[str]
    secret: Optional[str] = None


class SSOConfigureRequest(BaseModel):
    provider: str
    metadata_url: str
    entity_id: str


class BillingPortalRequest(BaseModel):
    origin: str


@app.post("/api/org")
async def create_organization(
    body: CreateOrgRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if current_user.get("org_id"):
        raise HTTPException(status_code=400, detail="User already belongs to an organization.")
    org, membership = await org_service.create_org(session, body.name, current_user["id"])
    
    # Audit log
    await audit_service.log(
        session=session,
        org_id=org.id,
        user_id=current_user["id"],
        action="org.create",
        resource_type="organization",
        resource_id=str(org.id),
        details={"name": org.name, "slug": org.slug}
    )

    return {"message": "Organization created successfully.", "org_id": org.id, "slug": org.slug}


@app.get("/api/org")
async def get_org(
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    org = await org_service.get_user_org(session, current_user["id"])
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "custom_system_prompt": org.custom_system_prompt,
        "logo_url": org.logo_url,
        "primary_color": org.primary_color,
        "secondary_color": org.secondary_color,
        "custom_domain": org.custom_domain,
        "data_retention_days": org.data_retention_days,
        "sso_provider": org.sso_provider,
        "sso_metadata_url": org.sso_metadata_url,
        "sso_entity_id": org.sso_entity_id,
        "stripe_customer_id": org.stripe_customer_id,
        "subscription_status": org.subscription_status,
        "role": current_user.get("org_role")
    }


@app.patch("/api/org/settings")
async def update_org_settings(
    body: OrgSettingsUpdate,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    update_data = body.model_dump(exclude_unset=True)
    org = await org_service.update_org_settings(session, org_id, update_data)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    
    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="settings.update",
        resource_type="organization",
        resource_id=str(org_id),
        details={"updated_fields": list(update_data.keys())}
    )

    # Webhook
    from webhooks import webhook_service
    await webhook_service.trigger(
        org_id=org_id,
        event_type="settings.update",
        data={"updated_fields": list(update_data.keys())}
    )

    return {"message": "Settings updated successfully."}


@app.post("/api/org/invite")
async def invite_member(
    body: InviteMemberRequest,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    try:
        membership = await org_service.invite_member(
            session, org_id, body.email, body.role, current_user["id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="member.invite",
        resource_type="user",
        resource_id=str(membership.user_id),
        details={"email": body.email, "role": body.role}
    )

    # Webhook
    from webhooks import webhook_service
    await webhook_service.trigger(
        org_id=org_id,
        event_type="member.invited",
        data={"email": body.email, "role": body.role}
    )

    return {"message": f"Invitation sent to {body.email}.", "membership_id": membership.id}


@app.get("/api/org/members")
async def list_members(
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    members = await org_service.get_org_members(session, current_user["org_id"])
    return members


@app.patch("/api/org/members/{member_id}/role")
async def update_member_role(
    member_id: int,
    body: UpdateMemberRoleRequest,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    if body.role == "owner" or current_user.get("org_role") != "owner":
        if current_user.get("org_role") != "owner":
            raise HTTPException(status_code=403, detail="Only organization owners can change member roles to owner or modify roles.")

    try:
        await org_service.update_member_role(session, org_id, member_id, body.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="member.role_change",
        resource_type="user",
        resource_id=str(member_id),
        details={"new_role": body.role}
    )

    # Webhook
    from webhooks import webhook_service
    await webhook_service.trigger(
        org_id=org_id,
        event_type="member.role_changed",
        data={"user_id": member_id, "new_role": body.role}
    )

    return {"message": "Member role updated."}


@app.delete("/api/org/members/{member_id}")
async def remove_member(
    member_id: int,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    if member_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Use the leave endpoint to leave the organization.")

    try:
        await org_service.remove_member(session, org_id, member_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="member.remove",
        resource_type="user",
        resource_id=str(member_id)
    )

    # Webhook
    from webhooks import webhook_service
    await webhook_service.trigger(
        org_id=org_id,
        event_type="member.removed",
        data={"user_id": member_id}
    )

    return {"message": "Member removed from organization."}


@app.post("/api/org/leave")
async def leave_org(
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    if current_user.get("org_role") == "owner":
        raise HTTPException(status_code=400, detail="Owners cannot leave. Transfer ownership first.")

    try:
        await org_service.remove_member(session, org_id, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="member.leave",
        resource_type="user",
        resource_id=str(current_user["id"])
    )

    # Webhook
    from webhooks import webhook_service
    await webhook_service.trigger(
        org_id=org_id,
        event_type="member.left",
        data={"user_id": current_user["id"]}
    )

    return {"message": "You have left the organization."}


@app.post("/api/documents/{document_id}/share")
async def share_document_to_org(
    document_id: int,
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    success = await ingestion_service.share_document_to_org(current_user["id"], document_id, org_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to share document. Make sure you own it and it is not already shared.")

    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="document.share",
        resource_type="document",
        resource_id=str(document_id)
    )

    # Webhook
    from webhooks import webhook_service
    await webhook_service.trigger(
        org_id=org_id,
        event_type="document.shared",
        data={"document_id": document_id, "user_id": current_user["id"]}
    )

    # Invalidate BM25
    search_engine.invalidate_bm25_cache(current_user["id"], org_id)
    return {"message": "Document shared with organization successfully."}


@app.get("/api/org/documents")
async def get_org_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(config.DEFAULT_PAGE_SIZE, ge=1, le=config.MAX_PAGE_SIZE),
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    offset = (page - 1) * page_size
    org_id = current_user["org_id"]
    
    total = await session.scalar(
        select(func.count(Document.id)).where(Document.org_id == org_id, Document.visibility == "org")
    ) or 0

    result = await session.execute(
        select(Document)
        .where(Document.org_id == org_id, Document.visibility == "org")
        .order_by(Document.uploaded_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.scalars().all()
    items = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "org_id": r.org_id,
            "visibility": r.visibility,
            "shared_by": r.shared_by,
            "filename": r.filename,
            "doc_type": r.doc_type,
            "chunks": r.chunks,
            "characters": r.characters,
            "uploaded_at": str(r.uploaded_at) if r.uploaded_at else None,
        }
        for r in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": -(-total // page_size) if total else 0,
    }


@app.get("/api/org/audit-logs")
async def get_org_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(config.DEFAULT_PAGE_SIZE, ge=1, le=config.MAX_PAGE_SIZE),
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    return await audit_service.get_logs(session, current_user["org_id"], page=page, page_size=page_size)


@app.get("/api/auth/sso/{org_slug}")
async def sso_login(
    org_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    request_info = {
        "is_secure": request.url.scheme == "https",
        "http_host": request.url.netloc,
        "path_info": request.url.path,
        "query_params": dict(request.query_params),
    }
    url = await sso_service.get_sso_login_url(session, org_slug, request_info)
    return {"url": url}


@app.post("/api/auth/sso/{org_slug}/callback")
@app.get("/api/auth/sso/{org_slug}/callback")
async def sso_callback(
    org_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    form_params = {}
    if request.method == "POST":
        try:
            form_params = dict(await request.form())
        except Exception:
            pass

    request_info = {
        "is_secure": request.url.scheme == "https",
        "http_host": request.url.netloc,
        "path_info": request.url.path,
        "query_params": dict(request.query_params),
        "form_params": form_params,
    }
    
    auth_data = await sso_service.handle_sso_callback(session, org_slug, request_info)
    
    # Audit log
    await audit_service.log(
        session=session,
        org_id=auth_data["user"]["org_id"],
        user_id=auth_data["user"]["id"],
        action="user.sso_login",
        resource_type="user",
        resource_id=str(auth_data["user"]["id"]),
        details={"email": auth_data["user"]["email"]}
    )

    return auth_data


@app.post("/api/org/sso/configure")
async def configure_sso(
    body: SSOConfigureRequest,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    await sso_service.configure_sso(session, org_id, body.provider, body.metadata_url, body.entity_id)
    
    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="sso.configure",
        resource_type="organization",
        resource_id=str(org_id),
        details={"provider": body.provider}
    )

    return {"message": "SSO configured successfully."}


@app.post("/api/org/api-keys")
async def create_org_api_key(
    body: CreateAPIKeyRequest,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    import secrets
    import hashlib
    from datetime import datetime, timedelta

    org_id = current_user["org_id"]
    
    raw_key = f"{config.API_KEY_PREFIX}{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=body.expires_in_days)

    db_key = APIKey(
        org_id=org_id,
        user_id=current_user["id"],
        key_hash=key_hash,
        key_prefix=config.API_KEY_PREFIX,
        name=body.name,
        scopes_json=json.dumps(body.scopes) if body.scopes else None,
        expires_at=expires_at,
    )
    session.add(db_key)
    await session.flush()

    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="api_key.create",
        resource_type="api_key",
        resource_id=str(db_key.id),
        details={"name": body.name}
    )

    return {"id": db_key.id, "key": raw_key, "name": body.name, "expires_at": expires_at}


@app.get("/api/org/api-keys")
async def list_org_api_keys(
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(APIKey).where(APIKey.org_id == current_user["org_id"])
    res = await session.execute(stmt)
    keys = res.scalars().all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.key_prefix,
            "last_used_at": str(k.last_used_at) if k.last_used_at else None,
            "expires_at": str(k.expires_at) if k.expires_at else None,
            "is_active": k.is_active,
            "created_at": str(k.created_at) if k.created_at else None,
        }
        for k in keys
    ]


@app.delete("/api/org/api-keys/{key_id}")
async def revoke_org_api_key(
    key_id: int,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(APIKey).where(APIKey.id == key_id, APIKey.org_id == current_user["org_id"])
    res = await session.execute(stmt)
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found.")

    await session.delete(key)
    
    # Audit log
    await audit_service.log(
        session=session,
        org_id=current_user["org_id"],
        user_id=current_user["id"],
        action="api_key.revoke",
        resource_type="api_key",
        resource_id=str(key_id)
    )

    return {"message": "API key revoked successfully."}


@app.post("/api/org/webhooks")
async def create_webhook(
    body: CreateWebhookRequest,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    endpoint = await webhook_service.register(session, org_id, body.url, body.events, body.secret)
    
    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="webhook.create",
        resource_type="webhook",
        resource_id=str(endpoint.id),
        details={"url": body.url, "events": body.events}
    )

    return {
        "id": endpoint.id,
        "url": endpoint.url,
        "events": body.events,
        "secret": endpoint.secret,
        "message": "Webhook created successfully."
    }


@app.get("/api/org/webhooks")
async def list_webhooks(
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    endpoints = await webhook_service.get_endpoints(session, current_user["org_id"])
    return [
        {
            "id": ep.id,
            "url": ep.url,
            "events": json.loads(ep.events_json) if ep.events_json else [],
            "is_active": ep.is_active,
            "failure_count": ep.failure_count,
            "last_triggered_at": str(ep.last_triggered_at) if ep.last_triggered_at else None,
            "created_at": str(ep.created_at) if ep.created_at else None,
        }
        for ep in endpoints
    ]


@app.delete("/api/org/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    deleted = await webhook_service.delete_endpoint(session, org_id, webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found.")

    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="webhook.delete",
        resource_type="webhook",
        resource_id=str(webhook_id)
    )

    return {"message": "Webhook deleted successfully."}


@app.post("/api/org/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    stmt = select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.org_id == org_id)
    res = await session.execute(stmt)
    endpoint = res.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook not found.")

    payload = {
        "event": "test.ping",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "org_id": org_id,
        "data": {"message": "Hello from LexBot test ping!"}
    }
    
    success = await webhook_service.deliver(endpoint.id, endpoint.url, endpoint.secret, "test.ping", payload)
    
    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="webhook.test",
        resource_type="webhook",
        resource_id=str(webhook_id),
        details={"success": success}
    )

    return {"success": success, "message": "Test payload dispatched."}


@app.post("/api/org/retention/run")
async def run_org_retention(
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    stats = await retention_service.apply_retention(session, org_id)
    
    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="retention.run",
        resource_type="organization",
        resource_id=str(org_id),
        details={"stats": stats}
    )

    return stats


# ══════════════════════════════════════════════════════════════════════════════
#  LEGAL / COMPLIANCE (Phase 8)
# ══════════════════════════════════════════════════════════════════════════════

class DeleteDataRequest(BaseModel):
    password: str


@app.get("/api/legal/terms")
async def get_terms_of_service():
    return TERMS_OF_SERVICE


@app.get("/api/legal/privacy")
async def get_privacy_policy():
    return PRIVACY_POLICY


@app.get("/api/legal/dpa")
async def get_data_processing_agreement():
    return DPA


@app.get("/api/legal/disclaimer")
async def get_ai_disclaimer():
    return {
        "disclaimer": AI_DISCLAIMER,
        "disclaimer_short": DISCLAIMER_SHORT,
        "last_updated": LAST_UPDATED,
    }


@app.post("/api/account/delete-my-data")
async def delete_my_data(
    body: DeleteDataRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = current_user["id"]
    user = await session.get(User, user_id)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")

    from datetime import datetime, timezone
    from database import Message, Summary, LongTermMemory, Document, Analytics, FeatureUsage, Invoice, Obligation, SavedClause

    deleted = {}

    for model, label in [
        (Message, "messages"),
        (Summary, "summaries"),
        (LongTermMemory, "long_term_memories"),
        (Document, "documents"),
        (Analytics, "analytics"),
        (FeatureUsage, "feature_usage"),
        (Invoice, "invoices"),
        (Obligation, "obligations"),
        (SavedClause, "saved_clauses"),
    ]:
        stmt = select(model).where(model.user_id == user_id)
        rows = (await session.execute(stmt)).scalars().all()
        for r in rows:
            await session.delete(r)
        deleted[label] = len(rows)

    from sqlalchemy import delete as sa_delete
    await session.execute(sa_delete(OrgMembership).where(OrgMembership.user_id == user_id))

    await session.delete(user)
    await session.commit()

    logger.warning("GDPR Right to Delete exercised for user %s (id=%s)", current_user.get("email"), user_id)

    return {
        "message": "All personal data deleted successfully.",
        "deletion_timestamp": datetime.now(timezone.utc).isoformat(),
        "deleted_records": deleted,
    }


@app.get("/api/legal/versions")
async def get_legal_versions():
    return {
        "terms_of_service": TERMS_OF_SERVICE["version"],
        "privacy_policy": PRIVACY_POLICY["version"],
        "dpa": DPA["version"],
        "last_updated": LAST_UPDATED,
        "product": config.FIRM_NAME,
    }


@app.get("/api/org/branding")
async def get_org_branding(
    slug: Optional[str] = None,
    domain: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    if not slug and not domain:
        raise HTTPException(status_code=400, detail="Must provide org 'slug' or 'domain' query parameter.")

    stmt = select(Organization)
    if slug:
        stmt = stmt.where(Organization.slug == slug)
    else:
        stmt = stmt.where(Organization.custom_domain == domain)

    res = await session.execute(stmt)
    org = res.scalar_one_or_none()
    if not org:
        return {
            "name": config.FIRM_NAME,
            "logo_url": None,
            "primary_color": "navy blue",
            "secondary_color": None,
            "custom_domain": None,
            "sso_enabled": False,
        }

    return {
        "name": org.name,
        "logo_url": org.logo_url,
        "primary_color": org.primary_color,
        "secondary_color": org.secondary_color,
        "custom_domain": org.custom_domain,
        "sso_enabled": org.sso_provider is not None,
    }


@app.post("/api/org/branding/logo")
async def upload_branding_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    import shutil
    logo_dir = os.path.join(config.BASE_DIR, "static", "logos")
    os.makedirs(logo_dir, exist_ok=True)
    
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "png"
    logo_filename = f"logo_org_{org_id}.{file_ext}"
    logo_path = os.path.join(logo_dir, logo_filename)
    
    with open(logo_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    logo_url = f"/static/logos/{logo_filename}"
    await org_service.update_org_settings(session, org_id, {"logo_url": logo_url})

    # Audit log
    await audit_service.log(
        session=session,
        org_id=org_id,
        user_id=current_user["id"],
        action="settings.branding_logo",
        resource_type="organization",
        resource_id=str(org_id),
        details={"logo_url": logo_url}
    )

    return {"logo_url": logo_url, "message": "Branding logo uploaded successfully."}


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    db_ok = False
    try:
        from database import async_session_factory
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "product": "LexBot 3.0",
        "firm": config.FIRM_NAME,
        "version": "3.0.0",
        "database": "connected" if db_ok else "unreachable",
        "billing": "live" if config.BILLING_ENABLED else "demo",
        "llm_provider": config.DEFAULT_LLM_PROVIDER,
        "sentry": bool(config.SENTRY_DSN),
        "features": ["chat", "clauses", "comparison", "summarization", "obligations", "templates", "tables", "clause-library", "multi-model", "hybrid-search", "ocr"],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  FRONTEND STATIC FILES
# ══════════════════════════════════════════════════════════════════════════════

_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
_frontend_assets = os.path.join(_frontend_dist, "assets")
_frontend_index = os.path.join(_frontend_dist, "index.html")

if os.path.isdir(_frontend_assets):
    app.mount("/assets", StaticFiles(directory=_frontend_assets), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    if os.path.isfile(_frontend_index):
        return FileResponse(_frontend_index)
    return {"detail": "Frontend not built yet. Run: npm run build"}

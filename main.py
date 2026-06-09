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
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

import config
from datetime import datetime, timedelta, timezone

from database import init_db, get_session, Document, User, Message, Summary, Invoice, ContractTemplate, Obligation, SavedClause, FeatureUsage, WebhookEndpoint, APIKey, Organization, OrgMembership, DocumentAnnotation, DocShare, Notification
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
    setup_2fa,
    enable_2fa,
    disable_2fa,
    verify_totp_code,
    get_user_by_id_raw,
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


class TemplateCreateRequest(BaseModel):
    name: str
    description: str = ""
    template_type: str = "Custom"
    clauses: list[dict] = []


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_type: Optional[str] = None
    clauses: Optional[list[dict]] = None


class SaveClauseRequest(BaseModel):
    clause_type: str
    title: str = ""
    content: str
    source_document: str = ""
    notes: str = ""
    visibility: str = "personal"  # personal / org


class TableExtractRequest(BaseModel):
    document_name: str


class BillingPortalRequest(BaseModel):
    origin: str


class TimelineRequest(BaseModel):
    document_name: str


class CrossRefRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class ObligationRequest(BaseModel):
    document_name: str


class PrivilegeUpdateRequest(BaseModel):
    is_privileged: bool
    privilege_notes: str = ""


class AnnotationCreateRequest(BaseModel):
    document_id: int
    annotation_type: str = "highlight"  # highlight / comment / strikeout / underline
    page_number: int = 0
    selected_text: str = ""
    comment: str = ""
    color: str = "yellow"
    position_json: Optional[str] = None


class AnnotationUpdateRequest(BaseModel):
    comment: Optional[str] = None
    color: Optional[str] = None
    position_json: Optional[str] = None


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


@app.post("/api/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin, session: AsyncSession = Depends(get_session)):
    user = await get_user_by_email(session, body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Contact your administrator.")

    # 2FA check
    if user.get("is_2fa_enabled"):
        temp_token = create_access_token({"sub": str(user["id"]), "2fa_pending": True, "exp": datetime.utcnow() + timedelta(minutes=5)})
        return {"2fa_required": True, "temp_token": temp_token, "user_id": user["id"]}

    token = create_access_token({"sub": str(user["id"])})
    safe_user = {k: v for k, v in user.items() if k != "hashed_password"}
    return Token(access_token=token, token_type="bearer", user=safe_user)


@app.get("/api/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {k: v for k, v in current_user.items() if k != "hashed_password"}


# ══════════════════════════════════════════════════════════════════════════════
#  2FA ENDPOINTS (Plan 3)
# ══════════════════════════════════════════════════════════════════════════════

class TwoFASetupResponse(BaseModel):
    secret: str
    uri: str
    qr_b64: Optional[str] = None


class TwoFAVerifyRequest(BaseModel):
    code: str


class TwoFALoginRequest(BaseModel):
    temp_token: str
    code: str


@app.post("/api/auth/2fa/setup")
async def setup_2fa_endpoint(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await setup_2fa(session, current_user["id"])
    import base64
    import io
    import qrcode
    qr = qrcode.make(result["uri"])
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return TwoFASetupResponse(secret=result["secret"], uri=result["uri"], qr_b64=qr_b64)


@app.post("/api/auth/2fa/verify")
async def verify_2fa_endpoint(body: TwoFAVerifyRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await enable_2fa(session, current_user["id"], body.code)
    return result


@app.post("/api/auth/2fa/disable")
async def disable_2fa_endpoint(body: TwoFAVerifyRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await disable_2fa(session, current_user["id"], body.code)
    return result


@app.post("/api/auth/2fa/login")
@limiter.limit("10/minute")
async def login_2fa(request: Request, body: TwoFALoginRequest, session: AsyncSession = Depends(get_session)):
    from jose import JWTError
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired 2FA token.")
    try:
        payload = jwt.decode(body.temp_token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        if not payload.get("2fa_pending"):
            raise credentials_exception
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    raw_user = await get_user_by_id_raw(session, int(user_id))
    if not raw_user or not raw_user.is_active or not raw_user.totp_secret:
        raise credentials_exception
    if not verify_totp_code(raw_user.totp_secret, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA code.")

    token = create_access_token({"sub": str(user_id)})
    user_dict = {k: v for k, v in (await get_user_by_email(session, raw_user.email) or {}).items() if k != "hashed_password"}
    return Token(access_token=token, token_type="bearer", user=user_dict)


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
#  CHAT STREAMING (Phase 5)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/chat/stream")
async def chat_stream(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Streaming version of /api/chat.
    Returns Server-Sent Events (SSE).
    Frontend listens with EventSource or fetch + ReadableStream.
    """
    session_id = body.session_id or str(uuid.uuid4())
    return StreamingResponse(
        rag_chain.query_stream(
            question=body.question,
            user_id=current_user["id"],
            session_id=session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
#  VOICE / SPEECH-TO-TEXT (Plan 2)
# ══════════════════════════════════════════════════════════════════════════════

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/mp4", "audio/mpeg", "audio/x-m4a", "audio/mp3"}


@app.post("/api/voice/transcribe")
async def transcribe_voice(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not config.ENABLE_VOICE:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Voice transcription is disabled.")

    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported audio type '{file.content_type}'. Allowed: webm, ogg, wav, mp4, mpeg, m4a, mp3.")

    contents = await file.read()
    if len(contents) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file exceeds 25MB limit.")

    try:
        import httpx
        groq_api = config.GROQ_API_KEY
        model = config.WHISPER_MODEL

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {groq_api}"},
                files={"file": (file.filename or "audio.webm", contents, file.content_type or "audio/webm")},
                data={"model": model, "response_format": "json", "language": "en"},
            )

        if resp.status_code != 200:
            logger.error("Groq Whisper error: %s %s", resp.status_code, resp.text)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Speech-to-text service returned an error.")

        result = resp.json()
        text = result.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Speech-to-text returned empty result.")

        logger.info("Voice transcribed for user %s: %s", current_user["id"], text[:80])
        return {"text": text}

    except httpx.TimeoutException:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Speech-to-text service timed out.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Voice transcription failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Speech-to-text service is temporarily unavailable.")


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
#  PRIVILEGE LOCK (Plan 3)
# ══════════════════════════════════════════════════════════════════════════════

@app.patch("/api/documents/{document_id}/privilege")
async def update_document_privilege(
    document_id: int,
    body: PrivilegeUpdateRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user["id"])
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    await session.execute(
        update(Document).where(Document.id == document_id).values(
            is_privileged=body.is_privileged,
            privilege_notes=body.privilege_notes,
        )
    )
    from audit import audit_service
    await audit_service.log(
        session=session,
        org_id=current_user.get("org_id"),
        user_id=current_user["id"],
        action="document.privilege_update",
        resource_type="document",
        resource_id=str(document_id),
        details={"is_privileged": body.is_privileged},
    )
    action = "marked as privileged" if body.is_privileged else "privilege removed"
    return {"message": f"Document {action}."}


@app.get("/api/documents/privileged")
async def list_privileged_documents(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Document)
        .where(Document.user_id == current_user["id"], Document.is_privileged)
        .order_by(Document.uploaded_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "is_privileged": r.is_privileged,
            "privilege_notes": r.privilege_notes,
            "uploaded_at": str(r.uploaded_at) if r.uploaded_at else None,
        }
        for r in rows
    ]


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
#  SESSION PDF EXPORT (Phase 10)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/export/session/{session_id}")
async def export_session_pdf(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export a chat session as a professionally formatted PDF report.
    Includes all messages, sources cited, and risk flags raised.
    """
    user_id = current_user["id"]

    # Load session messages from SQLite
    messages_result = await session.execute(
        select(Message.role, Message.content, Message.created_at)
        .where(Message.user_id == user_id, Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = messages_result.all()

    summary_result = await session.execute(
        select(Summary.summary)
        .where(Summary.user_id == user_id, Summary.session_id == session_id)
        .order_by(Summary.updated_at.desc())
        .limit(1)
    )
    summary_row = summary_result.scalar_one_or_none()

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this session.")

    # Build PDF with reportlab
    from fastapi.responses import StreamingResponse as FileStreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.units import mm
    from datetime import datetime

    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    NAVY = HexColor("#0f172a")
    LIGHT_GRAY = HexColor("#f8fafc")
    MID_GRAY = HexColor("#64748b")

    title_style = ParagraphStyle("Title", parent=styles["Normal"],
        fontSize=20, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=MID_GRAY, spaceAfter=16)
    section_style = ParagraphStyle("Section", parent=styles["Normal"],
        fontSize=11, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    q_style = ParagraphStyle("Question", parent=styles["Normal"],
        fontSize=10, textColor=NAVY, fontName="Helvetica-Bold",
        backColor=LIGHT_GRAY, borderPad=6, spaceAfter=4)
    a_style = ParagraphStyle("Answer", parent=styles["Normal"],
        fontSize=10, textColor=black, leading=15, spaceAfter=12)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"],
        fontSize=9, textColor=MID_GRAY, spaceAfter=16)

    story = []

    # Header
    story.append(Paragraph(f"{config.FIRM_NAME}", title_style))
    story.append(Paragraph("Legal Research Session Report", subtitle_style))
    story.append(Paragraph(
        f"Session ID: {session_id[:12]}...  |  Exported: {datetime.now().strftime('%d %b %Y %H:%M')}  |  User: {current_user['username']}",
        meta_style
    ))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 12))

    # Summary if available
    if summary_row:
        story.append(Paragraph("Session summary", section_style))
        story.append(Paragraph(summary_row.summary, a_style))
        story.append(HRFlowable(width="100%", thickness=0.3, color=LIGHT_GRAY))
        story.append(Spacer(1, 8))

    # Messages
    story.append(Paragraph("Research transcript", section_style))
    msg_list = [{"role": m.role, "content": m.content} for m in messages]
    qa_pairs = []
    i = 0
    while i < len(msg_list):
        if msg_list[i]["role"] == "human":
            q = msg_list[i]
            a = msg_list[i+1] if i+1 < len(msg_list) and msg_list[i+1]["role"] == "assistant" else None
            qa_pairs.append((q, a))
            i += 2 if a else 1
        else:
            i += 1

    for idx, (q, a) in enumerate(qa_pairs, 1):
        story.append(Paragraph(f"Q{idx}: {q['content']}", q_style))
        if a:
            answer_text = a["content"][:2000].replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(answer_text, a_style))
        story.append(Spacer(1, 6))

    # Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"This report was generated by {config.FIRM_NAME} LexBot 2.0. "
        "All answers are based solely on uploaded documents and should be reviewed by a qualified legal professional.",
        meta_style
    ))

    pdf_doc.build(story)
    buffer.seek(0)

    safe_session = session_id[:8]
    return FileStreamingResponse(
        iter([buffer.read()]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="session_{safe_session}_report.pdf"'
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ANNOTATED PDF EXPORT (Plan 2)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/annotations")
async def create_annotation(body: AnnotationCreateRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    annotation = DocumentAnnotation(
        user_id=current_user["id"],
        document_id=body.document_id,
        annotation_type=body.annotation_type,
        page_number=body.page_number,
        selected_text=body.selected_text,
        comment=body.comment,
        color=body.color,
        position_json=body.position_json,
    )
    session.add(annotation)
    await session.flush()
    return {
        "id": annotation.id,
        "message": f"{body.annotation_type} annotation created.",
    }


@app.get("/api/annotations")
async def list_annotations(
    document_id: int = Query(...),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DocumentAnnotation)
        .where(DocumentAnnotation.document_id == document_id, DocumentAnnotation.user_id == current_user["id"])
        .order_by(DocumentAnnotation.created_at.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "document_id": r.document_id,
            "annotation_type": r.annotation_type,
            "page_number": r.page_number,
            "selected_text": r.selected_text,
            "comment": r.comment,
            "color": r.color,
            "position_json": r.position_json,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]


@app.patch("/api/annotations/{annotation_id}")
async def update_annotation(annotation_id: int, body: AnnotationUpdateRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(DocumentAnnotation).where(DocumentAnnotation.id == annotation_id, DocumentAnnotation.user_id == current_user["id"])
    )
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found.")
    updates = {}
    if body.comment is not None:
        updates["comment"] = body.comment
    if body.color is not None:
        updates["color"] = body.color
    if body.position_json is not None:
        updates["position_json"] = body.position_json
    if updates:
        await session.execute(update(DocumentAnnotation).where(DocumentAnnotation.id == annotation_id).values(**updates))
    return {"message": "Annotation updated."}


@app.delete("/api/annotations/{annotation_id}")
async def delete_annotation(annotation_id: int, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(DocumentAnnotation).where(DocumentAnnotation.id == annotation_id, DocumentAnnotation.user_id == current_user["id"])
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found.")
    await session.execute(delete(DocumentAnnotation).where(DocumentAnnotation.id == annotation_id))
    return {"message": "Annotation deleted."}


@app.get("/api/export/document/{document_id}/annotated")
async def export_annotated_document_pdf(
    document_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    doc_result = await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user["id"])
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    annotations_result = await session.execute(
        select(DocumentAnnotation)
        .where(DocumentAnnotation.document_id == document_id, DocumentAnnotation.user_id == current_user["id"])
        .order_by(DocumentAnnotation.created_at.asc())
    )
    annotations = annotations_result.scalars().all()

    from fastapi.responses import StreamingResponse as FileStreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.units import mm

    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    NAVY = HexColor("#0f172a")
    AMBER = HexColor("#f59e0b")
    LIGHT_GRAY = HexColor("#f8fafc")
    MID_GRAY = HexColor("#64748b")
    HIGHLIGHT_YELLOW = HexColor("#fef3c7")
    HIGHLIGHT_GREEN = HexColor("#d1fae5")
    HIGHLIGHT_RED = HexColor("#fee2e2")
    HIGHLIGHT_BLUE = HexColor("#dbeafe")

    COLOR_MAP = {
        "yellow": HIGHLIGHT_YELLOW,
        "green": HIGHLIGHT_GREEN,
        "red": HIGHLIGHT_RED,
        "blue": HIGHLIGHT_BLUE,
    }

    title_style = ParagraphStyle("Title", parent=styles["Normal"], fontSize=18, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=10, textColor=MID_GRAY, spaceAfter=12)
    section_style = ParagraphStyle("Section", parent=styles["Normal"], fontSize=12, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, textColor=black, leading=15, spaceAfter=8)
    annotation_style = ParagraphStyle("Annotation", parent=styles["Normal"], fontSize=9, textColor=NAVY, leading=13, spaceAfter=4)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=MID_GRAY, spaceAfter=16)

    story = []
    story.append(Paragraph(f"{config.FIRM_NAME}", title_style))
    story.append(Paragraph("Annotated Document Report", subtitle_style))
    story.append(Paragraph(f"Document: {document.filename}  |  User: {current_user['username']}", meta_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 12))

    if annotations:
        story.append(Paragraph(f"Annotations ({len(annotations)})", section_style))
        for ann in annotations:
            bg = COLOR_MAP.get(ann.color, HIGHLIGHT_YELLOW)
            label = ann.annotation_type.capitalize()
            story.append(Paragraph(
                f'<para backcolor="{bg.hexval()}"><b>{label}:</b> '
                f'{ann.selected_text[:200] if ann.selected_text else "(no text selected)"}</para>',
                annotation_style,
            ))
            if ann.comment:
                story.append(Paragraph(f"<i>Note: {ann.comment}</i>", meta_style))
            story.append(Spacer(1, 4))

        story.append(HRFlowable(width="100%", thickness=0.3, color=LIGHT_GRAY))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Document content", section_style))

    doc_text = await ingestion_service.get_document_text(document_id, current_user["id"])
    if doc_text:
        for line in doc_text.split("\n"):
            if line.strip():
                story.append(Paragraph(line.strip()[:500].replace("<", "&lt;").replace(">", "&gt;"), body_style))
    else:
        story.append(Paragraph("<i>Document text not available for direct embedding.</i>", body_style))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"This annotated report was generated by {config.FIRM_NAME} LexBot 2.0.",
        meta_style,
    ))

    pdf_doc.build(story)
    buffer.seek(0)

    safe_name = document.filename.replace(".", "_")
    return FileStreamingResponse(
        iter([buffer.read()]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_annotated.pdf"',
        },
    )


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
#  LEGAL TIMELINE BUILDER (Phase 6)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/timeline")
async def build_timeline(
    body: TimelineRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Extract all dates, deadlines, and obligations from a document
    and return them sorted chronologically.
    """
    user_id = current_user["id"]

    # Validate document exists for this user
    doc_row = await session.execute(
        select(Document.id).where(Document.user_id == user_id, Document.filename == body.document_name)
    )
    if not doc_row.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Document '{body.document_name}' not found.")

    # Retrieve all chunks from this document
    try:
        collection = ingestion_service.get_collection(user_id)
        results = collection.get(
            where={"source": body.document_name},
            include=["documents"]
        )
        all_text = "\n\n".join(results["documents"]) if results["documents"] else ""
    except Exception as e:
        raise HTTPException(status_code=503, detail="Could not read document chunks.")

    if not all_text.strip():
        return {"document_name": body.document_name, "events": [], "message": "No content found in this document."}

    # Ask LLM to extract timeline events
    from langchain_core.messages import HumanMessage
    import json as json_lib

    llm = llm_provider.get_llm(temperature=0)

    prompt = f"""You are a legal timeline extractor.
Read the following legal document and extract ALL dates, deadlines, durations, and time-bound obligations.

For each event return a JSON object with:
- "date": the date or duration as written in the document (e.g. "January 15, 2024", "30 days after signing", "3 years")
- "label": a short 5-word max label (e.g. "Agreement effective date", "Termination notice period")
- "detail": one sentence explaining this event

Return ONLY a valid JSON array of these objects. No preamble, no markdown, no explanation.
If no dates or deadlines are found, return an empty array: []

DOCUMENT:
{all_text[:6000]}
"""

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        events = json_lib.loads(raw.strip())
        if not isinstance(events, list):
            events = []
    except Exception as e:
        raise HTTPException(status_code=503, detail="AI service could not extract timeline.")

    return {
        "document_name": body.document_name,
        "total_events": len(events),
        "events": events,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MULTI-DOCUMENT CROSS-REFERENCE (Phase 8)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/cross-reference")
async def cross_reference(
    body: CrossRefRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Ask a question across ALL of the user's uploaded documents.
    Returns synthesized answer with per-document citations.
    """
    user_id = current_user["id"]
    session_id = body.session_id or str(uuid.uuid4())

    # Check user has documents
    docs_result = await session.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )
    doc_count = docs_result.scalar() or 0
    if doc_count == 0:
        return {
            "answer": "No documents uploaded yet. Please upload legal documents before using cross-reference search.",
            "sources": [],
            "documents_searched": 0,
            "session_id": session_id,
        }

    # Retrieve from ALL documents
    retriever = ingestion_service.get_all_documents_retriever(user_id, k=8)
    if not retriever:
        raise HTTPException(status_code=503, detail="Could not access document store.")

    try:
        chunks = retriever.invoke(body.question)
    except Exception:
        chunks = []

    if not chunks:
        return {
            "answer": "No relevant content found across your documents for this question.",
            "sources": [],
            "documents_searched": doc_count,
            "session_id": session_id,
        }

    # Build context grouped by document
    from collections import defaultdict
    doc_chunks = defaultdict(list)
    for chunk in chunks:
        meta = chunk.metadata or {}
        source = meta.get("source", "Unknown")
        doc_chunks[source].append(chunk)

    context_parts = []
    for doc_name, doc_chunk_list in doc_chunks.items():
        context_parts.append(f"=== FROM: {doc_name} ===")
        for c in doc_chunk_list:
            meta = c.metadata or {}
            context_parts.append(f"[Chunk {meta.get('chunk_index', '?')}]\n{c.page_content}")
    context = "\n\n".join(context_parts)

    # Generate synthesized answer
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = llm_provider.get_llm(temperature=0.1)

    system_content = f"""You are a legal document analyst for {config.FIRM_NAME}.
You have been given content from MULTIPLE legal documents. Answer the question by synthesizing information across all documents.

Rules:
1. Cite EVERY fact with [Document: filename, Chunk: N]
2. If different documents say different things, note the differences explicitly
3. Never fabricate information
4. Be professional and precise

CONTENT FROM ALL DOCUMENTS:
{context}
"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_content),
            HumanMessage(content=body.question)
        ])
        answer = response.content
    except Exception as e:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable.")

    # Build sources list
    sources = []
    for chunk in chunks:
        meta = chunk.metadata or {}
        sources.append({
            "document": meta.get("source", "Unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "preview": chunk.page_content[:200],
        })

    return {
        "answer": answer,
        "sources": sources,
        "documents_searched": doc_count,
        "documents_with_results": list(doc_chunks.keys()),
        "session_id": session_id,
    }


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
#  OBLIGATION TRACKER — AI Extraction + CSV Export (Phase 7)
# ══════════════════════════════════════════════════════════════════════════════

import csv as csv_module
import io as io_module

@app.post("/api/obligations")
async def extract_obligations_v2(
    body: ObligationRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Extract every obligation, responsibility, and deadline from a document,
    organized by which party must do what.
    """
    user_id = current_user["id"]

    doc_row = await session.execute(
        select(Document.id).where(Document.user_id == user_id, Document.filename == body.document_name)
    )
    if not doc_row.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Document '{body.document_name}' not found.")

    try:
        collection = ingestion_service.get_collection(user_id)
        results = collection.get(
            where={"source": body.document_name},
            include=["documents"]
        )
        all_text = "\n\n".join(results["documents"]) if results["documents"] else ""
    except Exception:
        raise HTTPException(status_code=503, detail="Could not read document.")

    if not all_text.strip():
        return {"document_name": body.document_name, "obligations": []}

    from langchain_core.messages import HumanMessage
    import json as json_lib

    llm = llm_provider.get_llm(temperature=0)

    prompt = f"""You are a legal obligation extractor.
Read this legal document and extract every obligation, duty, responsibility, and restriction.

For each obligation return a JSON object with:
- "party": who must do this (e.g. "Receiving Party", "Both Parties", "Disclosing Party")
- "obligation": what they must do (one clear sentence)
- "deadline": when it must be done, or "Ongoing" if continuous
- "consequence": what happens if not done, or "Not specified"
- "article": the article or section reference if visible (e.g. "Article 2.1")

Return ONLY a valid JSON array. No preamble, no markdown.

DOCUMENT:
{all_text[:6000]}
"""

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        obligations = json_lib.loads(raw.strip())
        if not isinstance(obligations, list):
            obligations = []
    except Exception:
        raise HTTPException(status_code=503, detail="AI service could not extract obligations.")

    return {
        "document_name": body.document_name,
        "total_obligations": len(obligations),
        "obligations": obligations,
    }


@app.get("/api/obligations/export")
async def export_obligations(
    document_name: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Re-runs obligation extraction and returns a downloadable CSV file.
    Usage: GET /api/obligations/export?document_name=contract.pdf
    """
    from fastapi.responses import StreamingResponse as FileStreamingResponse

    req_body = ObligationRequest(document_name=document_name)
    result = await extract_obligations_v2(req_body, current_user, session)

    obligations = result.get("obligations", [])

    output = io_module.StringIO()
    writer = csv_module.DictWriter(
        output,
        fieldnames=["party", "obligation", "deadline", "consequence", "article"]
    )
    writer.writeheader()
    for ob in obligations:
        writer.writerow({
            "party": ob.get("party", ""),
            "obligation": ob.get("obligation", ""),
            "deadline": ob.get("deadline", ""),
            "consequence": ob.get("consequence", ""),
            "article": ob.get("article", ""),
        })

    output.seek(0)
    safe_name = document_name.replace(".pdf", "").replace(".docx", "").replace(".txt", "")

    return FileStreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_obligations.csv"'
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
#  OBLIGATION TRACKER (Phase 4) — original
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
    org_id = current_user.get("org_id")
    conditions = [ContractTemplate.is_custom == False]
    if org_id:
        conditions.append((ContractTemplate.org_id == org_id) & (ContractTemplate.is_custom))
    from sqlalchemy import or_
    result = await session.execute(
        select(ContractTemplate).where(or_(*conditions)).order_by(ContractTemplate.name)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "description": r.description,
            "template_type": r.template_type,
            "clauses": json.loads(r.clauses_json) if r.clauses_json else [],
            "is_custom": r.is_custom,
            "org_id": r.org_id,
        }
        for r in rows
    ]


@app.post("/api/templates/create")
async def create_template(body: TemplateCreateRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must belong to an organization to create custom templates.")
    template = ContractTemplate(
        user_id=current_user["id"],
        org_id=org_id,
        name=body.name,
        description=body.description,
        template_type=body.template_type,
        clauses_json=json.dumps(body.clauses),
        is_custom=True,
    )
    session.add(template)
    await session.flush()
    return {"id": template.id, "message": f"Template '{body.name}' created."}


@app.put("/api/templates/{template_id}")
async def update_template(template_id: int, body: TemplateUpdateRequest, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ContractTemplate).where(ContractTemplate.id == template_id, ContractTemplate.is_custom, ContractTemplate.user_id == current_user["id"])
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom template not found.")
    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.template_type is not None:
        updates["template_type"] = body.template_type
    if body.clauses is not None:
        updates["clauses_json"] = json.dumps(body.clauses)
    if updates:
        await session.execute(update(ContractTemplate).where(ContractTemplate.id == template_id).values(**updates))
    return {"message": f"Template '{template.name}' updated."}


@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: int, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ContractTemplate).where(ContractTemplate.id == template_id, ContractTemplate.is_custom, ContractTemplate.user_id == current_user["id"])
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom template not found.")
    await session.execute(delete(ContractTemplate).where(ContractTemplate.id == template_id))
    return {"message": f"Template '{template.name}' deleted."}


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
    if body.visibility == "org" and not current_user.get("org_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must belong to an organization to share clauses.")
    clause = SavedClause(
        user_id=current_user["id"],
        org_id=current_user.get("org_id") if body.visibility == "org" else None,
        clause_type=body.clause_type,
        title=body.title or f"{body.clause_type} clause",
        content=body.content,
        source_document=body.source_document,
        notes=body.notes,
        visibility=body.visibility,
    )
    session.add(clause)
    await session.flush()
    return {"id": clause.id, "visibility": clause.visibility, "message": "Clause saved to library."}


@app.get("/api/clauses")
async def list_clauses(
    clause_type: Optional[str] = Query(None),
    benchmarks_only: bool = Query(False),
    scope: Optional[str] = Query("personal"),  # personal / org / all
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import or_
    user_id = current_user["id"]
    org_id = current_user.get("org_id")

    if scope == "org":
        if not org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must belong to an organization to view firm clauses.")
        query = select(SavedClause).where(SavedClause.org_id == org_id, SavedClause.visibility == "org")
    elif scope == "all":
        conditions = [SavedClause.user_id == user_id]
        if org_id:
            conditions.append((SavedClause.org_id == org_id) & (SavedClause.visibility == "org"))
        query = select(SavedClause).where(or_(*conditions))
    else:
        query = select(SavedClause).where(SavedClause.user_id == user_id, SavedClause.visibility == "personal")

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
            "visibility": r.visibility,
            "org_id": r.org_id,
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


@app.post("/api/clauses/{clause_id}/share")
async def share_clause_to_org(clause_id: int, current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must belong to an organization to share clauses.")
    result = await session.execute(
        select(SavedClause).where(SavedClause.id == clause_id, SavedClause.user_id == current_user["id"])
    )
    clause = result.scalar_one_or_none()
    if not clause:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clause not found.")
    await session.execute(
        update(SavedClause).where(SavedClause.id == clause_id).values(org_id=org_id, visibility="org")
    )
    return {"message": "Clause shared to firm library."}


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
    rate_limit_rpm: int = 60
    rate_limit_rpd: int = 1000


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
        rate_limit_rpm=body.rate_limit_rpm,
        rate_limit_rpd=body.rate_limit_rpd,
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
            "usage_count": k.usage_count or 0,
            "rate_limit_rpm": k.rate_limit_rpm,
            "rate_limit_rpd": k.rate_limit_rpd,
            "last_used_at": str(k.last_used_at) if k.last_used_at else None,
            "expires_at": str(k.expires_at) if k.expires_at else None,
            "is_active": k.is_active,
            "created_at": str(k.created_at) if k.created_at else None,
        }
        for k in keys
    ]


@app.get("/api/org/api-keys/usage")
async def org_api_key_usage(
    current_user: dict = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(APIKey).where(APIKey.org_id == current_user["org_id"], APIKey.is_active)
    res = await session.execute(stmt)
    keys = res.scalars().all()
    total_usage = sum(k.usage_count or 0 for k in keys)
    return {
        "total_keys": len(keys),
        "total_usage": total_usage,
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "usage_count": k.usage_count or 0,
                "rate_limit_rpd": k.rate_limit_rpd,
                "remaining_today": max(0, (k.rate_limit_rpd or 1000) - (k.usage_count or 0)),
            }
            for k in keys
        ],
    }


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
#  LANGUAGE DETECTION (Plan 2)
# ══════════════════════════════════════════════════════════════════════════════

from language_utils import detect_language, get_language_name


@app.post("/api/language/detect")
async def detect_language_endpoint(body: dict, current_user: dict = Depends(get_current_user)):
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No text provided.")
    lang = detect_language(text)
    return {"language": lang, "language_name": get_language_name(lang)}


@app.get("/api/languages")
async def list_languages(current_user: dict = Depends(get_current_user)):
    from language_utils import _LANGUAGE_NAMES
    return {"enabled": config.ENABLE_MULTILINGUAL, "languages": _LANGUAGE_NAMES}


# ══════════════════════════════════════════════════════════════════════════════
#  TENANT ISOLATION (Plan 4)
# ══════════════════════════════════════════════════════════════════════════════

from tenant import check_tenant_isolation


@app.get("/api/org/isolation")
async def tenant_isolation_status(current_user: dict = Depends(require_org_admin)):
    """Return tenant isolation report for the current org."""
    return check_tenant_isolation(current_user)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT PORTAL (Plan 4)
# ══════════════════════════════════════════════════════════════════════════════

def require_client(current_user: dict = Depends(get_current_user)):
    """Allow only client-role users."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client access required.")
    return current_user


@app.get("/api/client/documents")
async def client_list_documents(
    current_user: dict = Depends(require_client),
    session: AsyncSession = Depends(get_session),
):
    """List documents shared with the client."""
    stmt = select(DocShare).where(
        DocShare.client_user_id == current_user["id"],
        (DocShare.expires_at.is_(None)) | (DocShare.expires_at > func.now()),
    )
    res = await session.execute(stmt)
    shares = res.scalars().all()
    doc_ids = [s.document_id for s in shares]
    if not doc_ids:
        return []
    docs_stmt = select(Document).where(Document.id.in_(doc_ids))
    docs_res = await session.execute(docs_stmt)
    docs = {d.id: d for d in docs_res.scalars().all()}
    return [
        {
            "id": d.id,
            "title": docs[d.id].title,
            "filename": docs[d.id].filename,
            "created_at": str(docs[d.id].created_at) if docs[d.id].created_at else None,
            "shared_at": str(next(s.created_at for s in shares if s.document_id == d.id)),
            "can_ask_questions": next(s.can_ask_questions for s in shares if s.document_id == d.id),
        }
        for d in doc_ids if d in docs
    ]


@app.get("/api/client/documents/{doc_id}")
async def client_get_document(
    doc_id: int,
    current_user: dict = Depends(require_client),
    session: AsyncSession = Depends(get_session),
):
    """Get a shared document's details and content."""
    share_stmt = select(DocShare).where(
        DocShare.client_user_id == current_user["id"],
        DocShare.document_id == doc_id,
    )
    share_res = await session.execute(share_stmt)
    share = share_res.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Document not shared with you.")
    doc_stmt = select(Document).where(Document.id == doc_id)
    doc_res = await session.execute(doc_stmt)
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "id": doc.id,
        "title": doc.title,
        "filename": doc.filename,
        "content_preview": (doc.content or "")[:2000],
        "can_ask_questions": share.can_ask_questions,
    }


@app.post("/api/org/documents/{doc_id}/share")
async def share_document_with_client(
    doc_id: int,
    body: dict,
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    """Share a document with a client user (by email or user_id)."""
    client_email = body.get("email")
    client_user_id = body.get("client_user_id")
    can_ask = body.get("can_ask_questions", True)
    expires_in_days = body.get("expires_in_days")

    if not client_email and not client_user_id:
        raise HTTPException(status_code=400, detail="Provide email or client_user_id.")

    # Verify document ownership
    doc_stmt = select(Document).where(
        Document.id == doc_id,
        Document.user_id == current_user["id"],
    )
    doc_res = await session.execute(doc_stmt)
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or not yours.")

    # Find client
    if client_user_id:
        client = await session.get(User, client_user_id)
    else:
        client_stmt = select(User).where(User.email == client_email, User.role == "client")
        client_res = await session.execute(client_stmt)
        client = client_res.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client user not found.")

    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    # Create share
    share = DocShare(
        document_id=doc_id,
        client_user_id=client.id,
        shared_by_user_id=current_user["id"],
        can_ask_questions=can_ask,
        expires_at=expires_at,
    )
    session.add(share)
    await session.flush()

    return {"id": share.id, "client_user_id": client.id, "expires_at": str(expires_at) if expires_at else None}


@app.get("/api/org/documents/shared")
async def list_shared_documents(
    current_user: dict = Depends(require_org_member),
    session: AsyncSession = Depends(get_session),
):
    """List documents the current user has shared with clients."""
    stmt = select(DocShare).where(DocShare.shared_by_user_id == current_user["id"])
    res = await session.execute(stmt)
    shares = res.scalars().all()
    if not shares:
        return []
    doc_ids = list(set(s.document_id for s in shares))
    client_ids = list(set(s.client_user_id for s in shares))

    docs_stmt = select(Document).where(Document.id.in_(doc_ids))
    docs_res = await session.execute(docs_stmt)
    docs = {d.id: d for d in docs_res.scalars().all()}

    clients_stmt = select(User).where(User.id.in_(client_ids))
    clients_res = await session.execute(clients_stmt)
    clients = {c.id: c for c in clients_res.scalars().all()}

    return [
        {
            "id": s.id,
            "document_id": s.document_id,
            "document_title": docs[s.document_id].title if s.document_id in docs else None,
            "client_email": clients[s.client_user_id].email if s.client_user_id in clients else None,
            "client_name": clients[s.client_user_id].username if s.client_user_id in clients else None,
            "can_ask_questions": s.can_ask_questions,
            "expires_at": str(s.expires_at) if s.expires_at else None,
            "created_at": str(s.created_at),
        }
        for s in shares
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  WEBHOOK / WEBHOOK EVENT HANDLING
# ══════════════════════════════════════════════════════════════════════════════

from websocket_manager import manager
from fastapi import WebSocket, WebSocketDisconnect


@app.websocket("/ws/notifications")
async def websocket_notifications(ws: WebSocket):
    """Real-time notification WebSocket endpoint.
    Client must send auth token as first message: {"token": "<jwt>"}
    """
    await ws.accept()
    user_data = None
    try:
        # Expect first message to be auth
        data = await ws.receive_json()
        token = data.get("token", "")
        from jose import jwt as jose_jwt
        try:
            payload = jose_jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            user_id = payload.get("id")
            if not user_id:
                await ws.send_json({"error": "Invalid token"})
                await ws.close()
                return
            user_data = {"id": user_id}
        except Exception:
            await ws.send_json({"error": "Invalid token"})
            await ws.close()
            return

        await manager.connect(user_id, ws)
        await ws.send_json({"type": "connected", "message": "Notifications active"})

        # Keep alive / listen for pings
        while True:
            try:
                data = await ws.receive_text()
                if data == "ping":
                    await ws.send_text("pong")
            except WebSocketDisconnect:
                break
    except Exception:
        pass
    finally:
        if user_data:
            manager.disconnect(user_data["id"], ws)


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS (Plan 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/notifications")
async def list_notifications(
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Notification).where(Notification.user_id == current_user["id"])
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    stmt = stmt.order_by(Notification.created_at.desc()).limit(50)
    res = await session.execute(stmt)
    notifications = res.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "type": n.notification_type,
            "resource_type": n.resource_type,
            "resource_id": n.resource_id,
            "is_read": n.is_read,
            "created_at": str(n.created_at),
        }
        for n in notifications
    ]


@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user["id"],
    )
    res = await session.execute(stmt)
    notif = res.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.is_read = True
    await session.flush()
    return {"status": "read"}


@app.put("/api/notifications/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import update
    stmt = (
        update(Notification)
        .where(Notification.user_id == current_user["id"], Notification.is_read == False)
        .values(is_read=True)
    )
    await session.execute(stmt)
    return {"status": "all_read"}


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
        "features": ["chat", "clauses", "comparison", "summarization", "obligations", "templates", "tables", "clause-library", "multi-model", "hybrid-search", "ocr", "voice", "annotations", "multilingual"],
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

import json
import logging
from typing import AsyncGenerator, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func, Index,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

import config

logger = logging.getLogger(__name__)

engine = create_async_engine(
    config.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


# ── Organizations (Phase 6) ──────────────────────────────────────────────────
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    custom_system_prompt = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(50), nullable=True)
    secondary_color = Column(String(50), nullable=True)
    custom_domain = Column(String(255), unique=True, nullable=True, index=True)
    data_retention_days = Column(Integer, default=0)  # 0 = forever
    sso_provider = Column(String(50), nullable=True)
    sso_metadata_url = Column(String(500), nullable=True)
    sso_entity_id = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), default="free")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OrgMembership(Base):
    __tablename__ = "org_memberships"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), default="member")  # owner/admin/member/viewer
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    joined_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=False)

    __table_args__ = (
        Index("idx_org_memberships_org_user", "org_id", "user_id", unique=True),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_audit_logs_org_id", "org_id"),
        Index("idx_audit_logs_created_at", "created_at"),
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(50), nullable=False)  # e.g., "lxb_"
    name = Column(String(255), nullable=False)
    scopes_json = Column(Text, nullable=True)
    rate_limit_rpm = Column(Integer, default=60)  # requests per minute
    rate_limit_rpd = Column(Integer, default=1000)  # requests per day
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_api_keys_org_id", "org_id"),
    )


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(1000), nullable=False)
    secret = Column(String(255), nullable=False)  # for HMAC signing
    events_json = Column(Text, nullable=False)  # list of event types
    is_active = Column(Boolean, default=True)
    failure_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_webhooks_org_id", "org_id"),
    )


class DocShare(Base):
    """Share a document with a client (Plan 4 - Client Portal)."""
    __tablename__ = "doc_shares"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    client_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    can_ask_questions = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_doc_shares_client", "client_user_id", "document_id", unique=True),
    )


class Notification(Base):
    """In-app notification for real-time delivery (Plan 4)."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    notification_type = Column(String(50), default="info")  # info, warning, error, success
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_notifications_user_read", "user_id", "is_read"),
    )


# ── Users ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="lawyer")
    firm_name = Column(String(255), default="")
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Profile ─────────────────────────────────────────────────────────────────
    phone_number = Column(String(50), default="")
    avatar_url = Column(String(500), nullable=True)

    # ── 2FA (Plan 3) ────────────────────────────────────────────────────────────
    totp_secret = Column(String(255), nullable=True)
    is_2fa_enabled = Column(Boolean, default=False)

    # ── Billing ────────────────────────────────────────────────────────────────
    stripe_customer_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), default="free")
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_price_id = Column(String(255), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)


# ── Messages ───────────────────────────────────────────────────────────────────
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_messages_user_session", "user_id", "session_id"),
        Index("idx_messages_created_at", "created_at"),
    )


# ── Summaries ──────────────────────────────────────────────────────────────────
class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_summaries_user_session", "user_id", "session_id"),
    )


# ── Long-term memory ───────────────────────────────────────────────────────────
class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    memory_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_ltm_user_id", "user_id"),
    )


# ── Documents ──────────────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    visibility = Column(String(50), default="personal")  # "personal" or "org"
    shared_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(500), nullable=False)
    doc_type = Column(String(100), default="General")
    chunks = Column(Integer, default=0)
    characters = Column(Integer, default=0)
    is_privileged = Column(Boolean, default=False)
    privilege_notes = Column(Text, default="")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_documents_user_id", "user_id"),
        Index("idx_documents_user_filename", "user_id", "filename"),
        Index("idx_documents_org_id", "org_id"),
    )


# ── Document Chunks (pgvector) ────────────────────────────────────────────────
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    source = Column(String(500), nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_chunks_user_id", "user_id"),
        Index("idx_chunks_org_id", "org_id"),
        Index("idx_chunks_source", "source"),
    )


# ── Analytics ──────────────────────────────────────────────────────────────────
class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    sources_used = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_analytics_user_id", "user_id"),
        Index("idx_analytics_created_at", "created_at"),
    )


# ── Feature usage ──────────────────────────────────────────────────────────────
class FeatureUsage(Base):
    __tablename__ = "feature_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feature_name = Column(String(100), nullable=False)
    clause_type = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_feature_usage_user_id", "user_id"),
    )


# ── Obligations (Phase 4) ─────────────────────────────────────────────────────
class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    obligation_text = Column(Text, nullable=False)
    party_responsible = Column(String(500), default="")
    deadline = Column(String(255), nullable=True)
    obligation_type = Column(String(100), default="other")  # payment/delivery/reporting/compliance/other
    status = Column(String(50), default="pending")  # pending/completed/overdue
    source_document = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_obligations_user_id", "user_id"),
        Index("idx_obligations_status", "user_id", "status"),
    )


# ── Contract Templates (Phase 4) ──────────────────────────────────────────────
class ContractTemplate(Base):
    __tablename__ = "contract_templates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    template_type = Column(String(100), nullable=False)  # NDA/Employment/SaaS/Lease/Vendor/Custom
    clauses_json = Column(Text, nullable=False)  # JSON: [{type, description, required}]
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_templates_type", "template_type"),
        Index("idx_templates_org_id", "org_id"),
    )


# ── Saved Clauses (Phase 4) ───────────────────────────────────────────────────
class SavedClause(Base):
    __tablename__ = "saved_clauses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    clause_type = Column(String(100), nullable=False)
    title = Column(String(500), default="")
    content = Column(Text, nullable=False)
    source_document = Column(String(500), default="")
    notes = Column(Text, default="")
    is_benchmark = Column(Boolean, default=False)
    visibility = Column(String(50), default="personal")  # personal / org
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_saved_clauses_user_id", "user_id"),
        Index("idx_saved_clauses_type", "user_id", "clause_type"),
        Index("idx_clauses_org_id", "org_id"),
    )


# ── Document Annotations (Plan 2) ─────────────────────────────────────────────
class DocumentAnnotation(Base):
    __tablename__ = "document_annotations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    annotation_type = Column(String(50), nullable=False)  # highlight / comment / strikeout / underline
    page_number = Column(Integer, default=0)
    selected_text = Column(Text, default="")
    comment = Column(Text, default="")
    color = Column(String(50), default="yellow")
    position_json = Column(Text, nullable=True)  # JSON: {x, y, width, height} relative coords
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_annotations_doc_user", "document_id", "user_id"),
    )


# ── Invoices (Phase 5) ─────────────────────────────────────────────────────────
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_invoice_id = Column(String(255), nullable=True)
    amount_paid = Column(Integer, default=0)
    currency = Column(String(10), default="usd")
    status = Column(String(50), default="pending")
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    invoice_pdf = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Initialization ─────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Initialize DB by creating any missing tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")


# ── Session dependency ─────────────────────────────────────────────────────────
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

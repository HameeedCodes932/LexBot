"""
Multi-tenant isolation utilities (Plan 4).
Provides tenant-scoped query wrappers and middleware helpers.
"""

import logging
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import Document, Message, Summary, LongTermMemory, Analytics, Obligation, SavedClause

logger = logging.getLogger(__name__)


def scope_document_query(user_id: int, org_id: Optional[int] = None):
    """
    Return a WHERE clause that scopes document queries to:
    - the user's personal documents, OR
    - org-shared documents if org_id is set.
    """
    from sqlalchemy import or_
    conditions = [Document.user_id == user_id]
    if org_id:
        conditions.append(
            and_(Document.org_id == org_id, Document.visibility == "org")
        )
    return or_(*conditions)


def scope_messages_query(user_id: int):
    """Messages are always per-user."""
    return Message.user_id == user_id


def scope_obligations_query(user_id: int, org_id: Optional[int] = None):
    """Obligations are per-user only (no org sharing currently)."""
    return Obligation.user_id == user_id


def scope_clauses_query(user_id: int, org_id: Optional[int] = None):
    """Clauses: user's personal or org-shared."""
    from sqlalchemy import or_
    conditions = [and_(SavedClause.user_id == user_id, SavedClause.visibility == "personal")]
    if org_id:
        conditions.append(
            and_(SavedClause.org_id == org_id, SavedClause.visibility == "org")
        )
    return or_(*conditions)


def check_tenant_isolation(user: dict) -> dict:
    """Return a report of the user's tenant isolation status."""
    return {
        "user_id": user["id"],
        "org_id": user.get("org_id"),
        "org_role": user.get("org_role"),
        "data_isolation": {
            "documents": "org-scoped" if user.get("org_id") else "user-scoped",
            "messages": "user-scoped",
            "obligations": "user-scoped",
            "clauses": "org-scoped" if user.get("org_id") else "user-scoped",
            "chromadb": "separate collections per user/org",
            "database": "shared PostgreSQL with org_id FK",
        },
        "recommendation": (
            "Current soft-isolation is appropriate for most law firms. "
            "True schema-per-tenant would require separate PostgreSQL schemas."
        ),
    }

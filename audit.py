import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import AuditLog, User

logger = logging.getLogger(__name__)


class AuditService:
    async def log(
        self,
        session: AsyncSession,
        org_id: Optional[int],
        user_id: Optional[int],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        ip_address = None
        user_agent = None

        if request:
            # Try to get real IP from common reverse proxy headers
            ip_address = (
                request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                or request.headers.get("x-real-ip")
                or (request.client.host if request.client else None)
            )
            user_agent = request.headers.get("user-agent")

        details_str = json.dumps(details) if details else None

        log_entry = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details_json=details_str,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        session.add(log_entry)
        try:
            await session.flush()
            logger.info(f"AuditLog created: action={action} user={user_id} org={org_id}")
        except Exception as exc:
            logger.error(f"Failed to write audit log: {exc}")

        return log_entry

    async def get_logs(
        self,
        session: AsyncSession,
        org_id: int,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated audit logs for an organization with optional filters."""
        stmt = (
            select(AuditLog, User.username, User.email)
            .outerjoin(User, AuditLog.user_id == User.id)
            .where(AuditLog.org_id == org_id)
        )

        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if start_date:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        stmt = stmt.order_by(desc(AuditLog.created_at))

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        res = await session.execute(stmt)
        logs = []
        for log_entry, username, email in res:
            details = None
            if log_entry.details_json:
                try:
                    details = json.loads(log_entry.details_json)
                except Exception:
                    details = log_entry.details_json

            logs.append(
                {
                    "id": log_entry.id,
                    "org_id": log_entry.org_id,
                    "user_id": log_entry.user_id,
                    "username": username or "System/Deleted",
                    "email": email or "System/Deleted",
                    "action": log_entry.action,
                    "resource_type": log_entry.resource_type,
                    "resource_id": log_entry.resource_id,
                    "details": details,
                    "ip_address": log_entry.ip_address,
                    "user_agent": log_entry.user_agent,
                    "created_at": log_entry.created_at,
                }
            )

        return logs


audit_service = AuditService()

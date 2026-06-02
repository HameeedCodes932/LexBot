import logging
from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import Organization, OrgMembership, User, Message, Summary, LongTermMemory, Analytics, AuditLog

logger = logging.getLogger(__name__)


class RetentionService:
    async def apply_retention(self, session: AsyncSession, org_id: int) -> dict:
        """Enforce data retention policy for a single organization."""
        org = await session.get(Organization, org_id)
        if not org or org.data_retention_days <= 0:
            return {"status": "skipped", "message": "No retention policy set."}

        days = org.data_retention_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # 1. Fetch all user IDs in this organization
        member_stmt = select(User.id).where(User.org_id == org_id)
        res = await session.execute(member_stmt)
        user_ids = list(res.scalars().all())

        stats = {
            "messages_deleted": 0,
            "summaries_deleted": 0,
            "ltm_deleted": 0,
            "analytics_deleted": 0,
            "audit_logs_deleted": 0,
        }

        if user_ids:
            # 2. Delete messages
            msg_del = await session.execute(
                delete(Message).where(Message.user_id.in_(user_ids), Message.created_at < cutoff_date)
            )
            stats["messages_deleted"] = msg_del.rowcount

            # 3. Delete summaries
            sum_del = await session.execute(
                delete(Summary).where(Summary.user_id.in_(user_ids), Summary.updated_at < cutoff_date)
            )
            stats["summaries_deleted"] = sum_del.rowcount

            # 4. Delete long term memory
            ltm_del = await session.execute(
                delete(LongTermMemory).where(
                    LongTermMemory.user_id.in_(user_ids), LongTermMemory.created_at < cutoff_date
                )
            )
            stats["ltm_deleted"] = ltm_del.rowcount

            # 5. Delete analytics
            an_del = await session.execute(
                delete(Analytics).where(Analytics.user_id.in_(user_ids), Analytics.created_at < cutoff_date)
            )
            stats["analytics_deleted"] = an_del.rowcount

        # 6. Delete audit logs (which are org-scoped directly)
        audit_del = await session.execute(
            delete(AuditLog).where(AuditLog.org_id == org_id, AuditLog.created_at < cutoff_date)
        )
        stats["audit_logs_deleted"] = audit_del.rowcount

        logger.info(
            f"Applied retention policy ({days} days) for org {org_id} ({org.name}): {stats}"
        )
        return {
            "status": "success",
            "org_id": org_id,
            "org_name": org.name,
            "retention_days": days,
            "cutoff_date": cutoff_date.isoformat(),
            "deleted_counts": stats,
        }

    async def apply_all_retention_policies(self, session: AsyncSession) -> List[dict]:
        """Apply retention policy to all organizations with active policies."""
        stmt = select(Organization.id).where(Organization.data_retention_days > 0)
        res = await session.execute(stmt)
        org_ids = res.scalars().all()

        results = []
        for org_id in org_ids:
            try:
                res_dict = await self.apply_retention(session, org_id)
                results.append(res_dict)
            except Exception as exc:
                logger.error(f"Failed to apply retention policy for org {org_id}: {exc}")
                results.append({"status": "error", "org_id": org_id, "error": str(exc)})

        return results


retention_service = RetentionService()

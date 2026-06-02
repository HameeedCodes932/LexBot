import logging
import json
import hmac
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import WebhookEndpoint, async_session_factory

logger = logging.getLogger(__name__)


class WebhookService:
    async def register(
        self, session: AsyncSession, org_id: int, url: str, events: List[str], secret: Optional[str] = None
    ) -> WebhookEndpoint:
        """Register a new webhook endpoint for an organization."""
        import secrets
        if not secret:
            secret = f"whsec_{secrets.token_hex(24)}"

        endpoint = WebhookEndpoint(
            org_id=org_id,
            url=url,
            secret=secret,
            events_json=json.dumps(events),
            is_active=True,
            failure_count=0,
        )
        session.add(endpoint)
        await session.flush()
        logger.info(f"Registered webhook endpoint URL={url} for org {org_id}")
        return endpoint

    async def get_endpoints(self, session: AsyncSession, org_id: int) -> List[WebhookEndpoint]:
        """Get all webhook endpoints for an organization."""
        stmt = select(WebhookEndpoint).where(WebhookEndpoint.org_id == org_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def delete_endpoint(self, session: AsyncSession, org_id: int, endpoint_id: int) -> bool:
        """Remove a webhook endpoint."""
        stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id, WebhookEndpoint.org_id == org_id
        )
        res = await session.execute(stmt)
        endpoint = res.scalar_one_or_none()
        if not endpoint:
            return False
        await session.delete(endpoint)
        logger.info(f"Deleted webhook endpoint ID {endpoint_id} for org {org_id}")
        return True

    async def trigger(self, org_id: int, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger webhooks for a given event asynchronously (fire-and-forget)."""
        # Run inside a background task to not block the main request thread
        asyncio.create_task(self._process_trigger(org_id, event_type, data))

    async def _process_trigger(self, org_id: int, event_type: str, data: Dict[str, Any]) -> None:
        """Internal worker to fetch endpoints and trigger delivery."""
        async with async_session_factory() as session:
            stmt = select(WebhookEndpoint).where(
                WebhookEndpoint.org_id == org_id, WebhookEndpoint.is_active
            )
            res = await session.execute(stmt)
            endpoints = res.scalars().all()

            if not endpoints:
                return

            payload = {
                "event": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "org_id": org_id,
                "data": data,
            }

            tasks = []
            for ep in endpoints:
                events = []
                try:
                    events = json.loads(ep.events_json)
                except Exception:
                    pass

                # Match event type (wildcard "*" support)
                if "*" in events or event_type in events:
                    tasks.append(self.deliver(ep.id, ep.url, ep.secret, event_type, payload))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def deliver(
        self, endpoint_id: int, url: str, secret: str, event_type: str, payload: Dict[str, Any]
    ) -> bool:
        """Deliver payload to webhook URL with retries and signature verification."""
        body = json.dumps(payload)
        signature = hmac.new(
            secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-LexBot-Signature": signature,
            "X-LexBot-Event": event_type,
            "User-Agent": "LexBot-Webhook-Client/1.0",
        }

        retries = 3
        backoff = 2  # base exponential backoff factor

        async with httpx.AsyncClient(timeout=config.WEBHOOK_TIMEOUT_SECONDS) as client:
            for attempt in range(retries):
                try:
                    response = await client.post(url, content=body, headers=headers)
                    if response.status_code >= 200 and response.status_code < 300:
                        # Successful delivery
                        await self._update_endpoint_status(endpoint_id, success=True)
                        return True
                    else:
                        logger.warning(
                            f"Webhook endpoint {url} returned status code {response.status_code} "
                            f"(attempt {attempt + 1}/{retries})"
                        )
                except Exception as exc:
                    logger.warning(
                        f"Webhook delivery failed for {url}: {exc} (attempt {attempt + 1}/{retries})"
                    )

                if attempt < retries - 1:
                    await asyncio.sleep(backoff ** attempt)

        # All retries failed
        await self._update_endpoint_status(endpoint_id, success=False)
        return False

    async def _update_endpoint_status(self, endpoint_id: int, success: bool) -> None:
        """Update last triggered timestamp, failure count, and possibly auto-disable endpoint."""
        async with async_session_factory() as session:
            endpoint = await session.get(WebhookEndpoint, endpoint_id)
            if not endpoint:
                return

            endpoint.last_triggered_at = datetime.now(timezone.utc)
            if success:
                endpoint.failure_count = 0
            else:
                endpoint.failure_count += 1
                if endpoint.failure_count >= config.WEBHOOK_MAX_FAILURES:
                    endpoint.is_active = False
                    logger.warning(
                        f"Webhook endpoint {endpoint.url} auto-disabled after {endpoint.failure_count} consecutive failures."
                    )

            session.add(endpoint)
            await session.commit()


webhook_service = WebhookService()

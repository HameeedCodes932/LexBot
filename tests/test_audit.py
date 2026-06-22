import json
from unittest.mock import AsyncMock, MagicMock

from audit import AuditService
from database import AuditLog


class TestAuditLog:
    async def test_creates_log_entry(self, mock_session):
        service = AuditService()
        entry = await service.log(
            session=mock_session,
            org_id=1,
            user_id=42,
            action="test.action",
            resource_type="document",
            resource_id="123",
            details={"key": "value"},
        )

        assert isinstance(entry, AuditLog)
        assert entry.org_id == 1
        assert entry.user_id == 42
        assert entry.action == "test.action"
        assert entry.resource_type == "document"
        assert entry.resource_id == "123"
        assert json.loads(entry.details_json) == {"key": "value"}
        mock_session.add.assert_called_once_with(entry)
        mock_session.flush.assert_awaited_once()

    async def test_log_without_optional_fields(self, mock_session):
        service = AuditService()
        entry = await service.log(
            session=mock_session,
            org_id=None,
            user_id=None,
            action="system.event",
        )

        assert entry.org_id is None
        assert entry.user_id is None
        assert entry.details_json is None
        assert entry.ip_address is None
        assert entry.user_agent is None

    async def test_log_with_request_headers(self, mock_session, mock_request):
        mock_request.headers.get.side_effect = lambda key, default=None: {
            "x-forwarded-for": "203.0.113.42",
            "user-agent": "TestAgent/1.0",
        }.get(key, default)

        service = AuditService()
        entry = await service.log(
            session=mock_session,
            org_id=1,
            user_id=42,
            action="test.action",
            request=mock_request,
        )

        assert entry.ip_address == "203.0.113.42"
        assert entry.user_agent == "TestAgent/1.0"


class TestGetLogs:
    async def test_returns_paginated_logs(self, mock_session):
        log = MagicMock(
            id=1, org_id=1, user_id=42,
            action="test.action", resource_type="doc",
            resource_id="123", details_json='{"k":"v"}',
            ip_address="1.2.3.4", user_agent="Test",
            created_at="2026-01-01",
        )
        mock_result = MagicMock()
        mock_result.__iter__.return_value = [(log, "testuser", "test@test.com")]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuditService()
        logs = await service.get_logs(mock_session, org_id=1)

        assert len(logs) == 1
        assert logs[0]["username"] == "testuser"
        assert logs[0]["email"] == "test@test.com"
        assert logs[0]["action"] == "test.action"
        assert logs[0]["details"] == {"k": "v"}

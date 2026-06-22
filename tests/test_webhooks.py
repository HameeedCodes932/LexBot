import json
from unittest.mock import AsyncMock, MagicMock, patch

from webhooks import WebhookService
from database import WebhookEndpoint


class TestRegister:
    async def test_creates_endpoint_with_generated_secret(self, mock_session):
        service = WebhookService()
        ep = await service.register(
            mock_session, 1, "https://example.com/hook", ["query.completed"]
        )

        assert ep.url == "https://example.com/hook"
        assert ep.events_json == '["query.completed"]'
        assert ep.secret.startswith("whsec_")
        assert ep.is_active is True
        assert ep.failure_count == 0

    async def test_creates_endpoint_with_custom_secret(self, mock_session):
        service = WebhookService()
        ep = await service.register(
            mock_session, 1, "https://example.com/hook", ["*"], secret="mysecret"
        )

        assert ep.secret == "mysecret"
        assert ep.events_json == '["*"]'

    async def test_creates_endpoint_with_multiple_events(self, mock_session):
        service = WebhookService()
        events = ["document.uploaded", "document.deleted", "query.completed"]
        ep = await service.register(mock_session, 1, "https://example.com/hook", events)

        assert json.loads(ep.events_json) == events


class TestGetEndpoints:
    async def test_returns_empty_when_no_endpoints(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = WebhookService()
        endpoints = await service.get_endpoints(mock_session, 1)
        assert endpoints == []

    async def test_returns_endpoints(self, mock_session):
        mock_ep = MagicMock(id=1, url="https://example.com/hook")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_ep]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = WebhookService()
        endpoints = await service.get_endpoints(mock_session, 1)
        assert len(endpoints) == 1
        assert endpoints[0].id == 1


class TestDeliver:
    @patch("webhooks.httpx.AsyncClient")
    async def test_successful_delivery(self, mock_client_class, mock_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        mock_session.get = AsyncMock(return_value=MagicMock())

        service = WebhookService()
        result = await service.deliver(
            1, "https://example.com/hook", "secret", "test.ping",
            {"event": "test.ping", "data": {}}
        )
        assert result is True

    @patch("webhooks.httpx.AsyncClient")
    async def test_failed_delivery_retries(self, mock_client_class, mock_session):
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client_class.return_value = mock_client

        mock_session.get = AsyncMock(return_value=MagicMock())

        service = WebhookService()
        result = await service.deliver(
            1, "https://example.com/hook", "secret", "test.ping",
            {"event": "test.ping", "data": {}}
        )
        assert result is False
        assert mock_client.post.call_count == 3

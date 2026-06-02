import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime

import config
from main import app
from auth import get_current_user, require_admin
from database import get_session


# ── Override auth dependencies ─────────────────────────────────────────────────

@pytest.fixture
def mock_auth_user():
    """Override get_current_user to return a test user."""
    async def override():
        return {
            "id": 1,
            "username": "testuser",
            "email": "test@test.com",
            "role": "lawyer",
            "firm_name": "Test",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00",
            "stripe_customer_id": None,
            "subscription_status": "free",
        }
    app.dependency_overrides[get_current_user] = override
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_auth_admin():
    async def override():
        return {
            "id": 2,
            "username": "admin",
            "email": "admin@test.com",
            "role": "admin",
            "firm_name": "Admin",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00",
            "stripe_customer_id": None,
            "subscription_status": "free",
        }
    app.dependency_overrides[get_current_user] = override
    app.dependency_overrides[require_admin] = override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def mock_db_session():
    """Override get_session to return a mock."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()

    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    yield session
    app.dependency_overrides.pop(get_session, None)


# ── Health Check ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "features" in data
    assert isinstance(data["features"], list)


# ── Auth Endpoints ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_login_no_rate_limit(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "Nonexistent1",
        })
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_me_endpoint_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_me_authenticated(mock_auth_user, mock_db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@test.com"


# ── Billing Endpoints ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_billing_subscription_authenticated(mock_auth_user, mock_db_session):
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (None, "free", None)
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.scalar = AsyncMock(return_value=0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/billing/subscription")
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data
    assert "usage" in data


@pytest.mark.anyio
async def test_billing_invoices_authenticated(mock_auth_user, mock_db_session):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/billing/invoices")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_billing_create_checkout(mock_auth_user, mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/billing/create-checkout", json={
            "origin": "http://localhost:5173",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data


@pytest.mark.anyio
async def test_billing_portal(mock_auth_user, mock_db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/billing/portal", json={
            "origin": "http://localhost:5173",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data


# ── Feature Gating ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_free_user_blocked_from_clause_extraction(mock_auth_user, mock_db_session):
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (None, "free", None)
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.scalar = AsyncMock(return_value=0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/extract-clauses", json={
            "document_name": "test.pdf",
            "clause_type": "indemnification",
        })
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_free_user_blocked_from_comparison(mock_auth_user, mock_db_session):
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (None, "free", None)
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.scalar = AsyncMock(return_value=0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/compare-clauses", json={
            "document_one": "a.pdf",
            "document_two": "b.pdf",
            "clause_type": "indemnification",
        })
    assert resp.status_code == 403

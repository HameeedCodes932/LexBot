import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

# ── Async support ──────────────────────────────────────────────────────────────

@ pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Mock DB session ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.add = MagicMock()
    return session


# ── Mock user dict ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_user():
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "$2b$12$fakehash",
        "role": "lawyer",
        "firm_name": "Test Firm",
        "is_active": True,
        "created_at": "2026-01-01 00:00:00",
        "stripe_customer_id": None,
        "subscription_status": "free",
    }


@pytest.fixture
def mock_admin():
    return {
        "id": 2,
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$fakehash",
        "role": "admin",
        "firm_name": "Admin Firm",
        "is_active": True,
        "created_at": "2026-01-01 00:00:00",
        "stripe_customer_id": None,
        "subscription_status": "free",
    }


# ── Mock FastAPI Request ───────────────────────────────────────────────────────

@pytest.fixture
def mock_request():
    req = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers.get = MagicMock(return_value=None)
    return req


# ── Mock Token ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_token():
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake"

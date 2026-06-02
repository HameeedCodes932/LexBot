from unittest.mock import AsyncMock, MagicMock, patch

from billing import (
    get_user_plan,
    get_monthly_usage,
    check_feature_access,
    create_checkout_session,
    create_portal_session,
    get_or_create_customer,
    handle_webhook,
    _plan_for_price,
    _get_plan,
)
import config


class TestPlanHelpers:
    def test_plan_for_price(self):
        assert _plan_for_price("price_pro") == "pro"
        assert _plan_for_price("price_enterprise") == "enterprise"
        assert _plan_for_price("nonexistent") == "free"
        assert _plan_for_price(None) == "free"

    def test_get_plan(self):
        plan = _get_plan("free")
        assert plan["max_documents"] == 5
        assert plan["max_queries_monthly"] == 50

        plan = _get_plan("pro")
        assert plan["max_documents"] == 100

        plan = _get_plan("nonexistent")
        assert plan == config.PLANS["free"]


class TestGetUserPlan:
    async def test_free_plan_when_no_subscription(self, mock_session):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        plan = await get_user_plan(mock_session, 1)
        assert plan["plan_id"] == "free"
        assert plan["max_documents"] == 5

    async def test_active_pro_subscription(self, mock_session):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (None, "active", "price_pro")
        mock_session.execute.return_value = mock_result

        plan = await get_user_plan(mock_session, 1)
        assert plan["plan_id"] == "pro"
        assert plan["max_documents"] == 100

    async def test_canceled_subscription_falls_to_free(self, mock_session):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (None, "canceled", "price_pro")
        mock_session.execute.return_value = mock_result

        plan = await get_user_plan(mock_session, 1)
        assert plan["plan_id"] == "free"


class TestMonthlyUsage:
    async def test_returns_zeros_with_no_data(self, mock_session):
        mock_session.scalar = AsyncMock(return_value=0)

        usage = await get_monthly_usage(mock_session, 1)

        assert usage["queries_used"] == 0
        assert usage["documents_used"] == 0
        assert usage["feature_usage"]["extract-clauses"] == 0
        assert "period_start" in usage
        assert "period_end" in usage

    async def test_counts_usage_correctly(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [1]
        mock_session.execute.return_value = mock_result
        mock_session.scalar = AsyncMock()
        side_effects = [
            None,  # org_id
            42,    # queries count
            7,     # documents count
            3,     # extract-clauses
            1,     # compare-clauses
        ]
        mock_session.scalar.side_effect = side_effects

        usage = await get_monthly_usage(mock_session, 1)

        assert usage["queries_used"] == 42
        assert usage["documents_used"] == 7
        assert usage["feature_usage"]["extract-clauses"] == 3
        assert usage["feature_usage"]["compare-clauses"] == 1


class TestCheckFeatureAccess:
    async def test_free_user_blocked_from_extract(self, mock_session):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (None, "free", None)
        mock_session.execute.return_value = mock_result
        mock_session.scalar = AsyncMock(return_value=0)

        result = await check_feature_access(mock_session, 1, "extract-clauses")

        assert result["allowed"] is False
        assert result["reason"] == "upgrade_plan"

    async def test_free_user_can_chat(self, mock_session):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (None, "free", None)
        mock_session.execute.return_value = mock_result
        mock_session.scalar = AsyncMock(return_value=0)

        result = await check_feature_access(mock_session, 1, "chat")
        assert result["allowed"] is True

    async def test_blocked_when_over_query_limit(self, mock_session):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (None, "free", None)
        mock_session.execute.return_value = mock_result
        mock_session.scalar = AsyncMock(return_value=999)

        result = await check_feature_access(mock_session, 1, "chat")
        assert result["allowed"] is False
        assert result["reason"] == "query_limit"

    async def test_blocked_when_over_doc_limit(self, mock_session):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (None, "free", None)
        mock_session.execute.return_value = mock_result
        mock_session.scalar = AsyncMock(side_effect=[None, 0, 999, 0, 0])

        result = await check_feature_access(mock_session, 1, "documents")
        assert result["allowed"] is False
        assert result["reason"] == "doc_limit"

    async def test_pro_user_has_extract_access(self, mock_session):
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (None, "active", "price_pro")
        mock_session.execute.return_value = mock_result
        mock_session.scalar = AsyncMock(return_value=0)

        result = await check_feature_access(mock_session, 1, "extract-clauses")
        assert result["allowed"] is True


class TestCheckoutSession:
    @patch("billing.stripe", None)
    async def test_demo_mode_returns_local_url(self):
        url = await create_checkout_session(1, "price_pro", "http://localhost:5173")
        assert "billing?demo=upgrade" in url

    @patch("config.BILLING_ENABLED", True)
    @patch("billing.stripe")
    async def test_stripe_checkout_creates_session(self, mock_stripe):
        mock_stripe.checkout.Session.create.return_value.url = "https://stripe.com/checkout/test"
        url = await create_checkout_session(1, "price_pro", "http://localhost:5173")
        assert url == "https://stripe.com/checkout/test"


class TestPortalSession:
    @patch("billing.stripe", None)
    async def test_demo_mode_returns_local(self):
        url = await create_portal_session(1, "cus_demo", "http://localhost:5173")
        assert url.endswith("/billing")

    @patch("config.BILLING_ENABLED", True)
    @patch("billing.stripe")
    async def test_stripe_portal(self, mock_stripe):
        mock_stripe.billing_portal.Session.create.return_value.url = "https://stripe.com/portal/test"
        url = await create_portal_session(1, "cus_123", "http://localhost:5173")
        assert url == "https://stripe.com/portal/test"


class TestGetOrCreateCustomer:
    async def test_returns_existing_customer(self, mock_session):
        user = {"stripe_customer_id": "cus_existing"}
        result = await get_or_create_customer(mock_session, user)
        assert result == "cus_existing"

    @patch("billing.stripe", None)
    async def test_demo_mode_returns_cus_demo(self, mock_session):
        user = {"stripe_customer_id": None, "email": "t@t.com", "username": "test", "id": 1}
        result = await get_or_create_customer(mock_session, user)
        assert result == "cus_demo"


class TestWebhook:
    @patch("billing.stripe", None)
    async def test_demo_mode(self):
        result = await handle_webhook(b"{}", "sig")
        assert result == {"status": "demo_mode"}

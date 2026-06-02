import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from database import (
    User, Message, Summary, LongTermMemory, Document,
    Analytics, FeatureUsage, Obligation, ContractTemplate,
    SavedClause, Invoice, Base,
)


class TestUserModel:
    def test_has_all_billing_fields(self):
        import sqlalchemy as sa
        cols = {c.name: c for c in User.__table__.columns}
        assert "stripe_customer_id" in cols
        assert "subscription_status" in cols
        assert "stripe_subscription_id" in cols
        assert "stripe_price_id" in cols
        assert "trial_end" in cols
        assert "current_period_end" in cols

    def test_core_fields(self):
        cols = {c.name: c for c in User.__table__.columns}
        assert "id" in cols
        assert "username" in cols
        assert "email" in cols
        assert "hashed_password" in cols
        assert "role" in cols
        assert "is_active" in cols
        assert "created_at" in cols

    def test_default_subscription_status(self):
        col = User.__table__.columns["subscription_status"]
        assert col.default.arg == "free"


class TestInvoiceModel:
    def test_has_required_fields(self):
        cols = {c.name: c for c in Invoice.__table__.columns}
        assert "id" in cols
        assert "user_id" in cols
        assert "stripe_invoice_id" in cols
        assert "amount_paid" in cols
        assert "status" in cols
        assert "invoice_pdf" in cols
        assert "created_at" in cols


class TestAllModelsRegistered:
    def test_models_have_tablenames(self):
        assert User.__tablename__ == "users"
        assert Message.__tablename__ == "messages"
        assert Summary.__tablename__ == "summaries"
        assert LongTermMemory.__tablename__ == "long_term_memory"
        assert Document.__tablename__ == "documents"
        assert Analytics.__tablename__ == "analytics"
        assert FeatureUsage.__tablename__ == "feature_usage"
        assert Obligation.__tablename__ == "obligations"
        assert ContractTemplate.__tablename__ == "contract_templates"
        assert SavedClause.__tablename__ == "saved_clauses"
        assert Invoice.__tablename__ == "invoices"

    def test_all_in_metadata(self):
        tables = Base.metadata.tables
        for name in [
            "users", "messages", "summaries", "long_term_memory",
            "documents", "analytics", "feature_usage", "obligations",
            "contract_templates", "saved_clauses", "invoices",
        ]:
            assert name in tables, f"Table {name} not in metadata"


import config


def test_config_has_required_settings():
    assert hasattr(config, "SECRET_KEY")
    assert hasattr(config, "DATABASE_URL")
    assert hasattr(config, "MAX_UPLOAD_SIZE")
    assert config.MAX_UPLOAD_SIZE == 10 * 1024 * 1024


def test_plan_definitions():
    assert "free" in config.PLANS
    assert "pro" in config.PLANS
    assert "enterprise" in config.PLANS
    assert config.PLANS["free"]["max_documents"] == 5
    assert config.PLANS["free"]["max_queries_monthly"] == 50
    assert config.PLANS["pro"]["max_documents"] == 100
    assert config.PLANS["pro"]["max_queries_monthly"] == 10000
    assert "chat" in config.PLANS["free"]["features"]
    assert "extract-clauses" in config.PLANS["pro"]["features"]


def test_cors_origins():
    assert isinstance(config.CORS_ORIGINS, list)
    assert len(config.CORS_ORIGINS) > 0


def test_jwt_config():
    assert config.ALGORITHM == "HS256"
    assert config.ACCESS_TOKEN_EXPIRE_MINUTES == 480


def test_pagination_defaults():
    assert config.DEFAULT_PAGE_SIZE == 20
    assert config.MAX_PAGE_SIZE == 100


def test_billing_enabled_depends_on_key():
    original = config.STRIPE_SECRET_KEY
    assert config.BILLING_ENABLED == bool(original and not original.startswith("sk_test_placeholder"))

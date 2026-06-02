"""Add enterprise features tables and columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create organizations table ─────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("custom_system_prompt", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("primary_color", sa.String(50), nullable=True),
        sa.Column("secondary_color", sa.String(50), nullable=True),
        sa.Column("custom_domain", sa.String(255), unique=True, nullable=True),
        sa.Column("data_retention_days", sa.Integer(), server_default=sa.text("0")),
        sa.Column("sso_provider", sa.String(50), nullable=True),
        sa.Column("sso_metadata_url", sa.String(500), nullable=True),
        sa.Column("sso_entity_id", sa.String(255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("subscription_status", sa.String(50), server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_index("idx_organizations_custom_domain", "organizations", ["custom_domain"], unique=True)

    # ── 2. Add columns to users table ─────────────────────────────────────────
    op.add_column("users", sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True))

    # ── 3. Create org_memberships table ───────────────────────────────────────
    op.create_table(
        "org_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column("invited_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false")),
    )
    op.create_index("idx_org_memberships_org_user", "org_memberships", ["org_id", "user_id"], unique=True)

    # ── 4. Create audit_logs table ────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_logs_org_id", "audit_logs", ["org_id"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── 5. Create api_keys table ──────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_api_keys_org_id", "api_keys", ["org_id"])
    op.create_index("idx_api_keys_hash", "api_keys", ["key_hash"], unique=True)

    # ── 6. Create webhook_endpoints table ─────────────────────────────────────
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("events_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("failure_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_webhooks_org_id", "webhook_endpoints", ["org_id"])

    # ── 7. Modify documents table ─────────────────────────────────────────────
    op.add_column("documents", sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True))
    op.add_column("documents", sa.Column("visibility", sa.String(50), server_default="personal"))
    op.add_column("documents", sa.Column("shared_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.create_index("idx_documents_org_id", "documents", ["org_id"])


def downgrade() -> None:
    # ── 7. Revert documents table changes ─────────────────────────────────────
    op.drop_index("idx_documents_org_id", table_name="documents")
    op.drop_column("documents", "shared_by")
    op.drop_column("documents", "visibility")
    op.drop_column("documents", "org_id")

    # ── 6. Revert webhook_endpoints table ─────────────────────────────────────
    op.drop_table("webhook_endpoints")

    # ── 5. Revert api_keys table ──────────────────────────────────────────────
    op.drop_table("api_keys")

    # ── 4. Revert audit_logs table ────────────────────────────────────────────
    op.drop_table("audit_logs")

    # ── 3. Revert org_memberships table ───────────────────────────────────────
    op.drop_table("org_memberships")

    # ── 2. Revert users table changes ─────────────────────────────────────────
    op.drop_column("users", "org_id")

    # ── 1. Revert organizations table ─────────────────────────────────────────
    op.drop_table("organizations")

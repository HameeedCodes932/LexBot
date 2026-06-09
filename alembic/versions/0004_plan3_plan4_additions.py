"""Add Plan 3 & Plan 4 columns and tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_has_column(table: str, column: str) -> bool:
    """Check if a column exists in a table using the inspector."""
    from alembic.operations.ops import MigrationScript
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table in inspector.get_table_names()


def upgrade() -> None:
    # ── 1. Users table: 2FA columns ───────────────────────────────────────────
    if not _table_has_column("users", "totp_secret"):
        op.add_column("users", sa.Column("totp_secret", sa.String(255), nullable=True))
    if not _table_has_column("users", "is_2fa_enabled"):
        op.add_column("users", sa.Column("is_2fa_enabled", sa.Boolean(), server_default=sa.text("false")))

    # ── 2. Documents: privilege lock columns ──────────────────────────────────
    if not _table_has_column("documents", "is_privileged"):
        op.add_column("documents", sa.Column("is_privileged", sa.Boolean(), server_default=sa.text("false")))
    if not _table_has_column("documents", "privilege_notes"):
        op.add_column("documents", sa.Column("privilege_notes", sa.Text(), server_default=""))

    # ── 3. API keys: rate limit & usage columns ───────────────────────────────
    if not _table_has_column("api_keys", "rate_limit_rpm"):
        op.add_column("api_keys", sa.Column("rate_limit_rpm", sa.Integer(), server_default=sa.text("60")))
    if not _table_has_column("api_keys", "rate_limit_rpd"):
        op.add_column("api_keys", sa.Column("rate_limit_rpd", sa.Integer(), server_default=sa.text("1000")))
    if not _table_has_column("api_keys", "usage_count"):
        op.add_column("api_keys", sa.Column("usage_count", sa.Integer(), server_default=sa.text("0")))

    # ── 4. Document annotations table ─────────────────────────────────────────
    if not _table_exists("document_annotations"):
        op.create_table(
            "document_annotations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("annotation_type", sa.String(50), nullable=False),
            sa.Column("page_number", sa.Integer(), server_default=sa.text("0")),
            sa.Column("selected_text", sa.Text(), server_default=""),
            sa.Column("comment", sa.Text(), server_default=""),
            sa.Column("color", sa.String(50), server_default="yellow"),
            sa.Column("position_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_annotations_doc_user", "document_annotations", ["document_id", "user_id"])

    # ── 5. Notifications table ────────────────────────────────────────────────
    if not _table_exists("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("notification_type", sa.String(50), server_default="info"),
            sa.Column("resource_type", sa.String(50), nullable=True),
            sa.Column("resource_id", sa.String(50), nullable=True),
            sa.Column("is_read", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_notifications_user_read", "notifications", ["user_id", "is_read"])

    # ── 6. Doc shares table ───────────────────────────────────────────────────
    if not _table_exists("doc_shares"):
        op.create_table(
            "doc_shares",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("client_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("shared_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("can_ask_questions", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_doc_shares_client", "doc_shares", ["client_user_id", "document_id"], unique=True)


def downgrade() -> None:
    if _table_exists("doc_shares"):
        op.drop_table("doc_shares")
    if _table_exists("notifications"):
        op.drop_table("notifications")
    if _table_exists("document_annotations"):
        op.drop_table("document_annotations")
    if _table_has_column("api_keys", "usage_count"):
        op.drop_column("api_keys", "usage_count")
    if _table_has_column("api_keys", "rate_limit_rpd"):
        op.drop_column("api_keys", "rate_limit_rpd")
    if _table_has_column("api_keys", "rate_limit_rpm"):
        op.drop_column("api_keys", "rate_limit_rpm")
    if _table_has_column("documents", "privilege_notes"):
        op.drop_column("documents", "privilege_notes")
    if _table_has_column("documents", "is_privileged"):
        op.drop_column("documents", "is_privileged")
    if _table_has_column("users", "is_2fa_enabled"):
        op.drop_column("users", "is_2fa_enabled")
    if _table_has_column("users", "totp_secret"):
        op.drop_column("users", "totp_secret")

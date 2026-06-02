"""Add billing fields, invoices, and Phase 4 tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── User billing columns ──────────────────────────────────────────────────
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("subscription_status", sa.String(50), server_default="free"))
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("stripe_price_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True))

    # ── Invoices ──────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True),
        sa.Column("amount_paid", sa.Integer(), server_default=sa.text("0")),
        sa.Column("currency", sa.String(10), server_default="usd"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invoice_pdf", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_invoices_user_id", "invoices", ["user_id"])

    # ── Phase 4: Obligations ──────────────────────────────────────────────────
    op.create_table(
        "obligations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("obligation_text", sa.Text(), nullable=False),
        sa.Column("party_responsible", sa.String(500), server_default=""),
        sa.Column("deadline", sa.String(255), nullable=True),
        sa.Column("obligation_type", sa.String(100), server_default="other"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("source_document", sa.String(500), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_obligations_user_id", "obligations", ["user_id"])
    op.create_index("idx_obligations_status", "obligations", ["user_id", "status"])

    # ── Phase 4: Contract Templates ──────────────────────────────────────────
    op.create_table(
        "contract_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("template_type", sa.String(100), nullable=False),
        sa.Column("clauses_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_templates_type", "contract_templates", ["template_type"])

    # ── Phase 4: Saved Clauses ────────────────────────────────────────────────
    op.create_table(
        "saved_clauses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("clause_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), server_default=""),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_document", sa.String(500), server_default=""),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("is_benchmark", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_saved_clauses_user_id", "saved_clauses", ["user_id"])
    op.create_index("idx_saved_clauses_type", "saved_clauses", ["user_id", "clause_type"])


def downgrade() -> None:
    op.drop_table("saved_clauses")
    op.drop_table("contract_templates")
    op.drop_table("obligations")
    op.drop_table("invoices")
    op.drop_column("users", "current_period_end")
    op.drop_column("users", "trial_end")
    op.drop_column("users", "stripe_price_id")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_customer_id")

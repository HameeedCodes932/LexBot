"""Add document_chunks table with pgvector embedding column

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table in inspector.get_table_names()


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if not _table_exists("document_chunks"):
        op.create_table(
            "document_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source", sa.String(500), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_chunks_user_id", "document_chunks", ["user_id"])
        op.create_index("idx_chunks_org_id", "document_chunks", ["org_id"])
        op.create_index("idx_chunks_source", "document_chunks", ["source"])
        op.create_index("idx_chunks_document_id", "document_chunks", ["document_id"])

        # Add vector column (pgvector type not available in plain SQLAlchemy)
        op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(384)")


def downgrade() -> None:
    if _table_exists("document_chunks"):
        op.drop_table("document_chunks")

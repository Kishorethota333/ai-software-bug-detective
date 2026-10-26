"""add persisted source chunks for RAG

Revision ID: 9d7e2f1c4a60
Revises: 8c3f1a2d9b71
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "9d7e2f1c4a60"
down_revision: Union[str, Sequence[str], None] = "8c3f1a2d9b71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "source_chunks" not in inspect(op.get_bind()).get_table_names():
        op.create_table(
            "source_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("upload_id", sa.String(length=32), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("source_name", sa.String(length=512), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["upload_id"], ["project_uploads.upload_id"]),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.UniqueConstraint("upload_id", "source_name", "chunk_index"),
        )
        op.create_index("ix_source_chunks_upload_id", "source_chunks", ["upload_id"])
        op.create_index("ix_source_chunks_owner_id", "source_chunks", ["owner_id"])
        op.create_index(
            "ix_source_chunks_owner_upload",
            "source_chunks",
            ["owner_id", "upload_id"],
        )


def downgrade() -> None:
    if "source_chunks" in inspect(op.get_bind()).get_table_names():
        op.drop_table("source_chunks")
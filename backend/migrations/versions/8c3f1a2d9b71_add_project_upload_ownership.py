"""add project upload ownership

Revision ID: 8c3f1a2d9b71
Revises: 657954b6d145
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "8c3f1a2d9b71"
down_revision: Union[str, Sequence[str], None] = "657954b6d145"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "project_uploads" not in inspect(op.get_bind()).get_table_names():
        op.create_table(
            "project_uploads",
            sa.Column("upload_id", sa.String(length=32), primary_key=True),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        )
        op.create_index(
            "ix_project_uploads_owner_id",
            "project_uploads",
            ["owner_id"],
        )


def downgrade() -> None:
    if "project_uploads" in inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_project_uploads_owner_id", table_name="project_uploads")
        op.drop_table("project_uploads")

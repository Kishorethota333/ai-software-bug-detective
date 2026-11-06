"""persist source test cases and execution history

Revision ID: a1b2c3d4e5f6
Revises: 9d7e2f1c4a60
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9d7e2f1c4a60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    upload_columns = {column["name"] for column in inspector.get_columns("project_uploads")}
    if "project_id" not in upload_columns:
        with op.batch_alter_table("project_uploads") as batch_op:
            batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_project_uploads_project_id_projects",
                "projects",
                ["project_id"],
                ["id"],
            )
        op.create_index("ix_project_uploads_project_id", "project_uploads", ["project_id"])

    test_case_columns = {column["name"] for column in inspect(bind).get_columns("test_cases")}
    with op.batch_alter_table("test_cases") as batch_op:
        if "bug_id" in test_case_columns:
            batch_op.alter_column("bug_id", existing_type=sa.Integer(), nullable=True)
        if "project_id" not in test_case_columns:
            batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_test_cases_project_id_projects",
                "projects",
                ["project_id"],
                ["id"],
            )
        if "upload_id" not in test_case_columns:
            batch_op.add_column(sa.Column("upload_id", sa.String(length=32), nullable=True))
            batch_op.create_foreign_key(
                "fk_test_cases_upload_id_project_uploads",
                "project_uploads",
                ["upload_id"],
                ["upload_id"],
            )
        if "source_key" not in test_case_columns:
            batch_op.add_column(sa.Column("source_key", sa.String(length=64), nullable=True))
            batch_op.create_unique_constraint(
                "uq_test_cases_upload_source_key",
                ["upload_id", "source_key"],
            )

    inspector = inspect(bind)
    test_case_indexes = {index["name"] for index in inspector.get_indexes("test_cases")}
    if "ix_test_cases_project_id" not in test_case_indexes:
        op.create_index("ix_test_cases_project_id", "test_cases", ["project_id"])
    if "ix_test_cases_upload_id" not in test_case_indexes:
        op.create_index("ix_test_cases_upload_id", "test_cases", ["upload_id"])
    if "ix_test_cases_project_upload" not in test_case_indexes:
        op.create_index(
            "ix_test_cases_project_upload",
            "test_cases",
            ["project_id", "upload_id"],
        )

    if "test_execution_history" not in inspect(bind).get_table_names():
        op.create_table(
            "test_execution_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("upload_id", sa.String(length=32), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("test_case_id", sa.Integer(), nullable=True),
            sa.Column("initiated_by", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("execution_mode", sa.String(length=40), nullable=False),
            sa.Column("total", sa.Integer(), nullable=False),
            sa.Column("passed", sa.Integer(), nullable=False),
            sa.Column("failed", sa.Integer(), nullable=False),
            sa.Column("errors", sa.Integer(), nullable=False),
            sa.Column("skipped", sa.Integer(), nullable=False),
            sa.Column("duration_seconds", sa.Float(), nullable=False),
            sa.Column("runtime_executed", sa.Boolean(), nullable=False),
            sa.Column("output", sa.Text(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=False),
            sa.Column("failure_reason", sa.Text(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["upload_id"], ["project_uploads.upload_id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"]),
            sa.ForeignKeyConstraint(["initiated_by"], ["users.id"]),
        )
        op.create_index(
            "ix_test_execution_history_upload_id",
            "test_execution_history",
            ["upload_id"],
        )
        op.create_index(
            "ix_test_execution_history_project_id",
            "test_execution_history",
            ["project_id"],
        )
        op.create_index(
            "ix_test_execution_history_initiated_by",
            "test_execution_history",
            ["initiated_by"],
        )
        op.create_index(
            "ix_test_execution_history_upload_created",
            "test_execution_history",
            ["upload_id", "started_at"],
        )
        op.create_index(
            "ix_test_execution_history_project_created",
            "test_execution_history",
            ["project_id", "started_at"],
        )


def downgrade() -> None:
    # Keep execution records and source test cases during rollback.
    pass

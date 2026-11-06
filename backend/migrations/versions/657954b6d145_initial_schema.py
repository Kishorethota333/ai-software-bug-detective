"""initial schema

Revision ID: 657954b6d145
Revises: 
Create Date: 2026-10-12 14:00:54.252776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '657954b6d145'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "projects" not in existing_tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("technology", sa.String(length=255), nullable=False),
            sa.Column("repository_url", sa.String(length=500), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        )

    if "bugs" not in existing_tables:
        op.create_table(
            "bugs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=220), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=False),
            sa.Column("reproduction_steps", sa.Text(), nullable=False),
            sa.Column("expected_result", sa.Text(), nullable=False),
            sa.Column("actual_result", sa.Text(), nullable=False),
            sa.Column("module", sa.String(length=120), nullable=False),
            sa.Column("environment", sa.String(length=120), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("reporter_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
        )

    if "bug_analysis" not in existing_tables:
        op.create_table(
            "bug_analysis",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bug_id", sa.Integer(), nullable=False),
            sa.Column("root_cause", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("affected_component", sa.String(length=180), nullable=False),
            sa.Column("possible_causes", sa.Text(), nullable=False),
            sa.Column("suggested_fix", sa.Text(), nullable=False),
            sa.Column("recommended_actions", sa.Text(), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["bug_id"], ["bugs.id"]),
        )

    if "test_cases" not in existing_tables:
        op.create_table(
            "test_cases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bug_id", sa.Integer(), nullable=False),
            sa.Column("scenario", sa.String(length=240), nullable=False),
            sa.Column("input_data", sa.Text(), nullable=False),
            sa.Column("expected_result", sa.Text(), nullable=False),
            sa.Column("priority", sa.String(length=20), nullable=False),
            sa.Column("test_type", sa.String(length=30), nullable=False),
            sa.Column("executed", sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(["bug_id"], ["bugs.id"]),
        )

    if "bug_attachments" not in existing_tables:
        op.create_table(
            "bug_attachments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bug_id", sa.Integer(), nullable=False),
            sa.Column("original_name", sa.String(length=255), nullable=False),
            sa.Column("stored_name", sa.String(length=255), nullable=False),
            sa.Column(
                "content_type",
                sa.String(length=120),
                nullable=False,
            ),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("extracted_text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["bug_id"], ["bugs.id"]),
        )

    indexes = (
        ("users", "ix_users_email", ["email"], True),
        ("projects", "ix_projects_name", ["name"], False),
        ("bugs", "ix_bugs_title", ["title"], False),
        ("bugs", "ix_bugs_project_id", ["project_id"], False),
        ("bug_analysis", "ix_bug_analysis_bug_id", ["bug_id"], False),
        ("test_cases", "ix_test_cases_bug_id", ["bug_id"], False),
        ("bug_attachments", "ix_bug_attachments_bug_id", ["bug_id"], False),
    )
    inspector = inspect(bind)
    for table_name, index_name, columns, unique in indexes:
        existing_indexes = {
            index["name"] for index in inspector.get_indexes(table_name)
        }
        if index_name not in existing_indexes:
            op.create_index(
                index_name,
                table_name,
                columns,
                unique=unique,
            )
            inspector = inspect(bind)


def downgrade() -> None:
    # This baseline also adopts databases created before Alembic was configured.
    # Dropping these tables could delete application data, so downgrade is non-destructive.
    pass

"""Add project metadata fields.

Revision ID: 003
Revises: 002
Create Date: 2026-03-10 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add metadata fields to projects table
    op.add_column("projects", sa.Column("client_name", sa.String(255), nullable=True))
    op.add_column("projects", sa.Column("client_address", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("contractor_name", sa.String(255), nullable=True))
    op.add_column("projects", sa.Column("contractor_address", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("author", sa.String(255), nullable=True))
    op.add_column("projects", sa.Column("checker", sa.String(255), nullable=True))
    op.add_column("projects", sa.Column("project_number", sa.String(100), nullable=True))
    op.add_column("projects", sa.Column("project_location", sa.String(255), nullable=True))
    op.add_column("projects", sa.Column("revision", sa.String(50), nullable=True))
    op.add_column("projects", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "notes")
    op.drop_column("projects", "revision")
    op.drop_column("projects", "project_location")
    op.drop_column("projects", "project_number")
    op.drop_column("projects", "checker")
    op.drop_column("projects", "author")
    op.drop_column("projects", "contractor_address")
    op.drop_column("projects", "contractor_name")
    op.drop_column("projects", "client_address")
    op.drop_column("projects", "client_name")

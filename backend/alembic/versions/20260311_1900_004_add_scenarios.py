"""Add scenarios table and link to calculation_runs.

Revision ID: 004
Revises: 003
Create Date: 2026-03-11 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scenarios table
    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("calculation_mode", sa.Enum("max", "min", name="calculationmode"), nullable=False, server_default="max"),
        sa.Column("element_states", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_scenarios_project_id", "scenarios", ["project_id"])

    # Add scenario_id to calculation_runs
    op.add_column(
        "calculation_runs",
        sa.Column("scenario_id", sa.String(36), sa.ForeignKey("scenarios.id", ondelete="SET NULL"), nullable=True)
    )
    op.create_index("ix_calculation_runs_scenario_id", "calculation_runs", ["scenario_id"])

    # Create default scenarios for existing projects
    # This is handled by the application on first access, not in migration
    # to avoid complex data migration logic


def downgrade() -> None:
    op.drop_index("ix_calculation_runs_scenario_id", "calculation_runs")
    op.drop_column("calculation_runs", "scenario_id")
    op.drop_index("ix_scenarios_project_id", "scenarios")
    op.drop_table("scenarios")
    # Note: The enum type 'calculationmode' already exists from calculation_runs

"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2026-03-10 15:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Network versions table
    op.create_table(
        'network_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('elements', sa.JSON(), nullable=False, default=dict),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Calculation runs table
    op.create_table(
        'calculation_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('network_version_id', sa.String(36), sa.ForeignKey('network_versions.id'), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('calculation_mode', sa.Enum('MAX', 'MIN', name='calculationmode'), nullable=False),
        sa.Column('fault_types', sa.JSON(), nullable=False, default=list),
        sa.Column('fault_buses', sa.JSON(), nullable=False, default=list),
        sa.Column('engine_version', sa.String(50), nullable=False),
        sa.Column('input_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='calculationstatus'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # Run results table
    op.create_table(
        'run_results',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('calculation_runs.id'), nullable=False, index=True),
        sa.Column('bus_id', sa.String(255), nullable=False, index=True),
        sa.Column('fault_type', sa.Enum('IK3', 'IK2', 'IK1', name='faulttype'), nullable=False),
        sa.Column('Ik', sa.Float(), nullable=False),
        sa.Column('ip', sa.Float(), nullable=False),
        sa.Column('R_X_ratio', sa.Float(), nullable=False),
        sa.Column('c_factor', sa.Float(), nullable=False),
        sa.Column('Zk', sa.JSON(), nullable=False),
        sa.Column('Z1', sa.JSON(), nullable=False),
        sa.Column('Z2', sa.JSON(), nullable=False),
        sa.Column('Z0', sa.JSON(), nullable=True),
        sa.Column('correction_factors', sa.JSON(), nullable=False, default=dict),
        sa.Column('warnings', sa.JSON(), nullable=False, default=list),
        sa.Column('assumptions', sa.JSON(), nullable=False, default=list),
    )


def downgrade() -> None:
    op.drop_table('run_results')
    op.drop_table('calculation_runs')
    op.drop_table('network_versions')
    op.drop_table('projects')
    op.drop_table('users')

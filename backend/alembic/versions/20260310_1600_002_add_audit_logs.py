"""Add audit_logs table

Revision ID: 002
Revises: 001
Create Date: 2026-03-10 16:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('action', sa.Enum(
            'LOGIN', 'LOGOUT', 'REGISTER', 'PASSWORD_CHANGE',
            'PROJECT_CREATE', 'PROJECT_UPDATE', 'PROJECT_DELETE',
            'VERSION_CREATE',
            'CALCULATION_START', 'CALCULATION_COMPLETE', 'CALCULATION_FAIL', 'CALCULATION_DELETE',
            'EXPORT_PDF', 'EXPORT_XLSX',
            name='auditaction'
        ), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False, default=dict),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')

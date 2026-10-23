"""feature flags: per-workspace overrides

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-23 17:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('feature_flags', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_column('feature_flags')

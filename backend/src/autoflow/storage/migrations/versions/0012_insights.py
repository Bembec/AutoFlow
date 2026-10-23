"""insights: time value and template origin

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-23 14:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('time_value_per_hour', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('time_value_currency', sa.String(length=3), server_default='USD', nullable=False))

    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_template', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.drop_column('source_template')

    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_column('time_value_currency')
        batch_op.drop_column('time_value_per_hour')

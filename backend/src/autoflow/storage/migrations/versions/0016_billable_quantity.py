"""billable quantity: one event can stand for several tasks (loops)

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-23 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('billable_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quantity', sa.Integer(), server_default=sa.text('1'), nullable=False))


def downgrade():
    with op.batch_alter_table('billable_events', schema=None) as batch_op:
        batch_op.drop_column('quantity')

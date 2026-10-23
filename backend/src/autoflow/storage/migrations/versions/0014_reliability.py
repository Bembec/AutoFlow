"""reliability: invoice voiding and connection health checks

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-23 16:00:00
"""

from alembic import op
import sqlalchemy as sa
import autoflow.storage.db


revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('voided_at', autoflow.storage.db.UTCDateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('void_reason', sa.Text(), nullable=True))

    with op.batch_alter_table('connections', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_checked_at', autoflow.storage.db.UTCDateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table('connections', schema=None) as batch_op:
        batch_op.drop_column('last_checked_at')

    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_column('void_reason')
        batch_op.drop_column('voided_at')

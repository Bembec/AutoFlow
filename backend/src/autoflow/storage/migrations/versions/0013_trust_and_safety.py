"""trust and safety: new-account trust, staff suspension, abuse reports

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-23 15:00:00
"""

from alembic import op
import sqlalchemy as sa
import autoflow.storage.db


revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('abuse_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=True),
    sa.Column('reporter_email', sa.String(length=320), nullable=True),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
    sa.Column('created_at', autoflow.storage.db.UTCDateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_abuse_reports_workspace_id_workspaces'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('abuse_reports', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_abuse_reports_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_abuse_reports_workspace_id'), ['workspace_id'], unique=False)

    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trusted_at', autoflow.storage.db.UTCDateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('staff_suspended_reason', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_column('staff_suspended_reason')
        batch_op.drop_column('trusted_at')

    with op.batch_alter_table('abuse_reports', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_abuse_reports_workspace_id'))
        batch_op.drop_index(batch_op.f('ix_abuse_reports_created_at'))

    op.drop_table('abuse_reports')

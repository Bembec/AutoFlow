"""quality samples: production evaluation of live AI results

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-23 21:00:00
"""

from alembic import op
import sqlalchemy as sa
import luphina.storage.db


revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('quality_samples',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('execution_id', sa.Integer(), nullable=False),
    sa.Column('workflow_id', sa.Integer(), nullable=False),
    sa.Column('step_id', sa.String(length=50), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('input', sa.JSON(), nullable=True),
    sa.Column('output', sa.JSON(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('verdict', sa.String(length=10), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', luphina.storage.db.UTCDateTime(timezone=True), nullable=True),
    sa.Column('created_at', luphina.storage.db.UTCDateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['execution_id'], ['workflow_executions.id'], name=op.f('fk_quality_samples_execution_id_workflow_executions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], name=op.f('fk_quality_samples_reviewed_by_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], name=op.f('fk_quality_samples_workflow_id_workflows'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_quality_samples_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('execution_id', 'step_id', name=op.f('uq_quality_samples_execution_id_step_id'))
    )
    with op.batch_alter_table('quality_samples', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_quality_samples_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_quality_samples_workspace_id'), ['workspace_id'], unique=False)

    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quality_sample_percent', sa.Integer(), server_default=sa.text('5'), nullable=False))


def downgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_column('quality_sample_percent')

    with op.batch_alter_table('quality_samples', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_quality_samples_workspace_id'))
        batch_op.drop_index(batch_op.f('ix_quality_samples_created_at'))

    op.drop_table('quality_samples')

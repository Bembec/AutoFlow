"""mcp server: workspace API keys and per-workflow opt-in

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-23 20:00:00
"""

from alembic import op
import sqlalchemy as sa
import autoflow.storage.db


revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('api_keys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('prefix', sa.String(length=16), nullable=False),
    sa.Column('key_hash', sa.String(length=64), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', autoflow.storage.db.UTCDateTime(timezone=True), nullable=False),
    sa.Column('last_used_at', autoflow.storage.db.UTCDateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', autoflow.storage.db.UTCDateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_api_keys_created_by_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_api_keys_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key_hash', name=op.f('uq_api_keys_key_hash'))
    )
    with op.batch_alter_table('api_keys', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_api_keys_workspace_id'), ['workspace_id'], unique=False)

    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mcp_enabled', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.drop_column('mcp_enabled')

    with op.batch_alter_table('api_keys', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_api_keys_workspace_id'))

    op.drop_table('api_keys')

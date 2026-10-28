"""rename the built-in webhook signature scheme to "luphina"

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-28 18:00:00
"""

from alembic import op


revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE webhook_endpoints SET signature_scheme = 'luphina' WHERE signature_scheme = 'autoflow'")


def downgrade():
    op.execute("UPDATE webhook_endpoints SET signature_scheme = 'autoflow' WHERE signature_scheme = 'luphina'")

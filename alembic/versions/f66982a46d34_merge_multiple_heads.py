"""merge multiple heads
Revision ID: f66982a46d34
Revises: ('6d8254780ead', '74e5e432f0a3')
Create Date: 2025-12-30 14:00:36.993733
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f66982a46d34'
down_revision = ('6d8254780ead', '74e5e432f0a3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

"""add workshop column to orders table

Revision ID: 6d8254780eac
Revises: 6d8254780eab
Create Date: 2025-12-26 12:41:17.123456

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6d8254780eac'
down_revision = '6d8254780eab'
branch_labels = None
depends_on = None


def upgrade():
    # 添加车间列到订单表
    op.add_column('orders', sa.Column('workshop', sa.String(length=255), nullable=True))


def downgrade():
    # 删除车间列
    op.drop_column('orders', 'workshop')
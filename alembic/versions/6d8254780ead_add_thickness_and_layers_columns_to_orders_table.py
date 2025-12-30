"""Add thickness and layers columns to orders table

Revision ID: 6d8254780ead
Revises: 6d8254780eac
Create Date: 2025-12-29 18:53:08.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '6d8254780ead'
down_revision = '6d8254780eac'
branch_labels = None
depends_on = None


def upgrade():
    # 添加thickness列
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column('thickness', sa.Float, nullable=True))
        batch_op.add_column(sa.Column('layers', sa.Integer, nullable=True))


def downgrade():
    # 删除thickness和layers列
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_column('layers')
        batch_op.drop_column('thickness')
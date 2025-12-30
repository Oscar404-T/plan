"""Add thickness column and remove layers column from orders table

Revision ID: 6d8254780eae
Revises: 6d8254780eac
Create Date: 2025-12-29 19:00:02.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '6d8254780eae'
down_revision = '6d8254780eac'
branch_labels = None
depends_on = None


def upgrade():
    # 检查并添加thickness列
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('orders')]
    
    if 'thickness' not in columns:
        op.add_column('orders',
                      sa.Column('thickness', sa.Float, nullable=True))
    
    # 检查并添加layers列（如果不存在）
    if 'layers' not in columns:
        op.add_column('orders',
                      sa.Column('layers', sa.Integer, nullable=True))


def downgrade():
    op.drop_column('orders', 'layers')
    op.drop_column('orders', 'thickness')
"""Add original_length and original_width fields to orders table

Revision ID: 6d8254780eaf
Revises: 6d8254780eae
Create Date: 2025-12-30 08:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '6d8254780eaf'
down_revision = '6d8254780eae'
branch_labels = None
depends_on = None


def upgrade():
    # 检查并添加original_length列
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('orders')]
    
    if 'original_length' not in columns:
        op.add_column('orders',
                      sa.Column('original_length', sa.Float, nullable=True))
    
    # 检查并添加original_width列
    if 'original_width' not in columns:
        op.add_column('orders',
                      sa.Column('original_width', sa.Float, nullable=True))


def downgrade():
    # 删除original_length和original_width列
    op.drop_column('orders', 'original_length')
    op.drop_column('orders', 'original_width')
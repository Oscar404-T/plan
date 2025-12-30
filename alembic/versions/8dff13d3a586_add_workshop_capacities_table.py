"""add workshop_capacities table

Revision ID: 8dff13d3a586
Revises: f66982a46d34
Create Date: 2025-12-30 14:02:22.784944

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8dff13d3a586'
down_revision = 'f66982a46d34'
branch_labels = None
depends_on = None


def upgrade():
    # 创建workshop_capacities表
    op.create_table('workshop_capacities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workshop', sa.String(length=255), nullable=False),
        sa.Column('operation_id', sa.Integer(), nullable=False),
        sa.Column('machine_name', sa.String(length=255), nullable=False),
        sa.Column('machine_count', sa.Integer(), nullable=False),
        sa.Column('cycle_time', sa.Float(), nullable=False),
        sa.Column('capacity_per_hour', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # 删除workshop_capacities表
    op.drop_table('workshop_capacities')

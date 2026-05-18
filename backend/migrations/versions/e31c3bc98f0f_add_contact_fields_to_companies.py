"""add contact fields to companies

Revision ID: e31c3bc98f0f
Revises: a9c9cc7d86bd
Create Date: 2026-05-17 11:22:35.503832
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e31c3bc98f0f'
down_revision = 'a9c9cc7d86bd'
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('email', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('phone', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('website', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('address', sa.Text(), nullable=True))


def downgrade():

    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_column('address')
        batch_op.drop_column('website')
        batch_op.drop_column('phone')
        batch_op.drop_column('email')
        batch_op.drop_column('description')
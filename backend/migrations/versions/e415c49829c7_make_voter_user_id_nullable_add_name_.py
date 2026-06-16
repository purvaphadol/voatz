"""make voter user_id nullable add name email columns

Revision ID: e415c49829c7
Revises: 10fbf823f419
Create Date: 2026-05-25 14:25:43.200430

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e415c49829c7'
down_revision = '10fbf823f419'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('voters', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('email', sa.String(length=150), nullable=True))

        batch_op.alter_column(
            'user_id',
            existing_type=sa.INTEGER(),
            nullable=True
        )

def downgrade():
    with op.batch_alter_table('voters', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.INTEGER(),
            nullable=False
        )

        batch_op.drop_column('email')
        batch_op.drop_column('name')
"""add description icon status to modules and audit fields to module_action

Revision ID: b01e0021fdca
Revises: e31c3bc98f0f
Create Date: 2026-05-18 12:20:06.683131
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b01e0021fdca'
down_revision = 'e31c3bc98f0f'
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table('modules', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('description', sa.Text(), nullable=True)
        )

        batch_op.add_column(
            sa.Column('icon', sa.String(length=100), nullable=True)
        )


def downgrade():

    with op.batch_alter_table('modules', schema=None) as batch_op:
        batch_op.drop_column('icon')
        batch_op.drop_column('description')
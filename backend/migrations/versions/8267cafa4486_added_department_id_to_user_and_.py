"""Added department_id to User

Revision ID: 8267cafa4486
Revises: f1a2b3c4d5e6
Create Date: 2026-05-14 12:25:23.168650
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8267cafa4486'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('department_id', sa.Integer(), nullable=True)
        )

        batch_op.create_foreign_key(
            'fk_users_department_id',
            'departments',
            ['department_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_users_department_id',
            type_='foreignkey'
        )

        batch_op.drop_column('department_id')
"""replace is_active with status on modules and add audit fields to module_action

Revision ID: 10fbf823f419
Revises: b01e0021fdca
Create Date: 2026-05-18 12:25:55.784874
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '10fbf823f419'
down_revision = 'b01e0021fdca'
branch_labels = None
depends_on = None


def upgrade():

    # Add audit fields to module_action
    with op.batch_alter_table('module_action', schema=None) as batch_op:

        batch_op.add_column(
            sa.Column('created_at', sa.DateTime(), nullable=True)
        )

        batch_op.add_column(
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )

        batch_op.add_column(
            sa.Column('created_by', sa.Integer(), nullable=True)
        )

        batch_op.add_column(
            sa.Column('updated_by', sa.Integer(), nullable=True)
        )

    # Remove old is_active column
    with op.batch_alter_table('modules', schema=None) as batch_op:

        batch_op.drop_column('is_active')


def downgrade():

    # Restore old is_active column
    with op.batch_alter_table('modules', schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                'is_active',
                sa.Boolean(),
                nullable=False,
                server_default=sa.true()
            )
        )

    # Remove audit fields
    with op.batch_alter_table('module_action', schema=None) as batch_op:

        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
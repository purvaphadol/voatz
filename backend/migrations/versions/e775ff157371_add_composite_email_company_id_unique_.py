"""add composite email company_id unique constraint

Revision ID: e775ff157371
Revises: 8267cafa4486
Create Date: 2026-05-14 15:29:07.567618
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e775ff157371'
down_revision = '8267cafa4486'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Drop old global unique constraint on email
        batch_op.drop_constraint('users_email_key', type_='unique')

        # Create company-wise unique constraint
        batch_op.create_unique_constraint(
            'uq_user_email_company',
            ['email', 'company_id']
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Remove company-wise unique constraint
        batch_op.drop_constraint(
            'uq_user_email_company',
            type_='unique'
        )

        # Restore old global email unique constraint
        batch_op.create_unique_constraint(
            'users_email_key',
            ['email']
        )
"""add is_protected flag to roles

Revision ID: 20519437d6ed
Revises: 10fbf823f419
Create Date: 2026-05-20

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20519437d6ed'
down_revision = '10fbf823f419'
branch_labels = None
depends_on = None


def upgrade():
    # Add column
    op.add_column(
        'roles',
        sa.Column(
            'is_protected',
            sa.Boolean(),
            nullable=False,
            server_default='false'
        )
    )

    # Mark Super Admin role as protected
    op.execute("""
        UPDATE roles
        SET is_protected = true
        WHERE lower(role_name) = 'super admin'
    """)


def downgrade():
    op.drop_column('roles', 'is_protected')
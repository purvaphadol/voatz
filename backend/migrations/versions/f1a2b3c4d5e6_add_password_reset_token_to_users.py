"""Add password_reset_token and password_reset_expires_at to users table

Revision ID: f1a2b3c4d5e6
Revises: dbbd9957c922
Create Date: 2026-04-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'dbbd9957c922'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users',
        sa.Column('password_reset_token', sa.String(length=64), nullable=True)
    )
    op.add_column('users',
        sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True)
    )
    op.create_index(
        op.f('ix_users_password_reset_token'),
        'users',
        ['password_reset_token'],
        unique=False
    )


def downgrade():
    op.drop_index(op.f('ix_users_password_reset_token'), table_name='users')
    op.drop_column('users', 'password_reset_expires_at')
    op.drop_column('users', 'password_reset_token')

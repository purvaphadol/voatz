"""add status governance indexes and tracking columns

Revision ID: 4f8b92c10a12
Revises: ec7d80a0b86c
Create Date: 2026-08-11 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '4f8b92c10a12'
down_revision = 'ec7d80a0b86c'
branch_labels = None
depends_on = None

tables_for_tracking = [
    'departments', 'roles', 'users', 'voters', 'elections', 'ballots',
    'candidates', 'user_role_mapping', 'role_permission_mapping',
    'user_permission_mapping', 'company_modules', 'voter_registrations',
    'companies', 'system_modules', 'system_module_actions', 'administrators',
    'audit_logs', 'verifications', 'votes'
]

def upgrade():
    # 1. Add tracking columns to tables
    for table in tables_for_tracking:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('deactivated_by_cascade_from_type', sa.String(length=50), nullable=True))
            batch_op.add_column(sa.Column('deactivated_by_cascade_from_id', sa.Integer(), nullable=True))

    # 2. Add missing composite indexes
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.create_index('idx_departments_company_status', ['company_id', 'status'], unique=False)

    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.create_index('idx_roles_company_status', ['company_id', 'status'], unique=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index('idx_users_company_status', ['company_id', 'status'], unique=False)

    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.create_index('idx_companies_status', ['status'], unique=False)

    with op.batch_alter_table('voters', schema=None) as batch_op:
        batch_op.create_index('idx_voters_company_status', ['company_id', 'status'], unique=False)


def downgrade():
    with op.batch_alter_table('voters', schema=None) as batch_op:
        batch_op.drop_index('idx_voters_company_status')

    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_index('idx_companies_status')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('idx_users_company_status')

    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_index('idx_roles_company_status')

    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.drop_index('idx_departments_company_status')

    for table in tables_for_tracking:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column('deactivated_by_cascade_from_id')
            batch_op.drop_column('deactivated_by_cascade_from_type')

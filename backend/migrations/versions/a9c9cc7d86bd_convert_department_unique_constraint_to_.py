"""convert department unique constraint to partial unique index

Revision ID: a9c9cc7d86bd
Revises: 58e87c2dd0d6
Create Date: 2026-05-15 17:31:25.128501

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9c9cc7d86bd'
down_revision = '58e87c2dd0d6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.drop_constraint(
            'unique_department_per_company', type_='unique'
        )

    # Partial index — only enforces uniqueness for active rows
    op.execute("""
        CREATE UNIQUE INDEX uq_dept_name_company_active
        ON departments (department_name, company_id)
        WHERE status = 1
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_dept_name_company_active")

    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'unique_department_per_company',
            ['department_name', 'company_id']
        )
        
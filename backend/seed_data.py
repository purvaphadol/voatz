"""
seed_data.py — Bootstrap the Voatz database with an Administrator and at
least one demo company (Datagrid / Company A).

The core seeding logic is factored into seed_company(), which can be
reused directly by test scripts to seed additional companies against the
live database without going through the HTTP API (which would fail for
Administrator-issued role-creation calls because create_role() uses
get_current_company_id() → None for admin tokens).
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from datetime import datetime
import os
import re
import getpass
from dotenv import load_dotenv

load_dotenv()
DATABASE_URI = os.environ["DATABASE_URL"]
masked_uri = re.sub(r':([^@]+)@', ':****@', DATABASE_URI)
print(f"Connecting to database: {masked_uri}")

engine = create_engine(DATABASE_URI)
metadata = MetaData()
metadata.reflect(bind=engine)
Session = sessionmaker(bind=engine)


# ---------------------------------------------------------------------------
# Reusable company-seeding function
# ---------------------------------------------------------------------------

MODULE_NAMES = [
    ("Dashboard",           1),
    ("Users",               2),
    ("Roles",               3),
    ("Departments",         4),
    ("Companies",           5),
    ("Modules",             6),
    ("Permissions",         7),
    ("UserRoles",           8),
    ("Settings",            9),
    ("Voters",              10),
    ("Elections",           11),
    ("Ballots",             12),
    ("Candidates",          13),
    ("Votes",               14),
    ("VoterRegistrations",  15),
    ("AuditLogs",           16),
]

ACTIONS = [
    {"name": "view",   "url": "/view"},
    {"name": "create", "url": "/create"},
    {"name": "update", "url": "/update"},
    {"name": "delete", "url": "/delete"},
]


def seed_company(
    session,
    company_name,
    super_admin_email,
    super_admin_password,
    super_admin_name="Super Admin",
    regular_admin_email=None,
    regular_admin_password=None,
    regular_admin_name="Admin",
):
    """Seed a complete company, including:

    - Company row
    - 'Admin' department
    - Protected 'Company Super Admin' role (is_super_admin=True, no dept)
    - Optional regular 'Admin' role (department-linked)
    - One super-admin user mapped to the super-admin role
    - Optional regular admin user mapped to the regular role
    - Full Modules / ModuleActions fan-out for this company
    - Full RolePermissionMapping grant for the super-admin role

    Returns a dict of all created IDs so callers can reference them later.
    """
    t = metadata.tables

    now = datetime.now()

    # 1. Company
    company_id = session.execute(
        t["companies"].insert().values(
            company_name=company_name,
            created_at=now,
            updated_at=now,
            status=1,
        ).returning(t["companies"].c.id)
    ).scalar()

    # 2. Department
    department_id = session.execute(
        t["departments"].insert().values(
            department_name="Admin",
            company_id=company_id,
            created_at=now,
            updated_at=now,
            status=1,
        ).returning(t["departments"].c.id)
    ).scalar()

    # 3a. Protected Company Super Admin role (no department)
    super_admin_role_id = session.execute(
        t["roles"].insert().values(
            role_name="Company Super Admin",
            department_id=None,
            is_super_admin=True,
            company_id=company_id,
            created_at=now,
            updated_at=now,
            status=1,
        ).returning(t["roles"].c.id)
    ).scalar()

    # 3b. Regular Admin role (optional, but always created for completeness)
    regular_role_id = session.execute(
        t["roles"].insert().values(
            role_name="Admin",
            department_id=department_id,
            is_super_admin=False,
            company_id=company_id,
            created_at=now,
            updated_at=now,
            status=1,
        ).returning(t["roles"].c.id)
    ).scalar()

    # 4a. Super-admin user
    super_user_id = session.execute(
        t["users"].insert().values(
            name=super_admin_name,
            email=super_admin_email,
            password_hash=generate_password_hash(super_admin_password),
            company_id=company_id,
            created_at=now,
            updated_at=now,
            status=1,
        ).returning(t["users"].c.id)
    ).scalar()

    session.execute(
        t["user_role_mapping"].insert().values(
            user_id=super_user_id,
            role_id=super_admin_role_id,
            department_id=department_id,
            company_id=company_id,
            status=1,
            created_at=now,
            updated_at=now,
        )
    )

    # 4b. Regular admin user (optional)
    regular_user_id = None
    if regular_admin_email and regular_admin_password:
        regular_user_id = session.execute(
            t["users"].insert().values(
                name=regular_admin_name,
                email=regular_admin_email,
                password_hash=generate_password_hash(regular_admin_password),
                company_id=company_id,
                created_at=now,
                updated_at=now,
                status=1,
            ).returning(t["users"].c.id)
        ).scalar()

        session.execute(
            t["user_role_mapping"].insert().values(
                user_id=regular_user_id,
                role_id=regular_role_id,
                department_id=department_id,
                company_id=company_id,
                status=1,
                created_at=now,
                updated_at=now,
            )
        )

    # 5. Modules
    module_rows = [
        {
            "module_name": name,
            "company_id": company_id,
            "status": 1,
            "order_index": idx,
            "created_at": now,
            "updated_at": now,
        }
        for name, idx in MODULE_NAMES
    ]
    module_ids = session.execute(
        t["modules"].insert().returning(t["modules"].c.id),
        module_rows,
    ).scalars().all()

    # 6. ModuleActions (view / create / update / delete for every module)
    module_action_rows = []
    for mod_id in module_ids:
        for act in ACTIONS:
            module_action_rows.append({
                "module_id": mod_id,
                "action_name": act["name"],
                "action_url": act["url"],
                "company_id": company_id,
                "status": 1,
                "created_at": now,
                "updated_at": now,
            })
    session.execute(t["module_action"].insert(), module_action_rows)

    # 7. RolePermissionMapping — grant all actions to the super-admin role
    all_actions = session.execute(
        t["module_action"].select().where(
            t["module_action"].c.company_id == company_id
        )
    ).fetchall()

    session.execute(
        t["role_permission_mapping"].insert(),
        [
            {
                "company_id": company_id,
                "role_id": super_admin_role_id,
                "module_id": row.module_id,
                "action_id": row.id,
                "status": 1,
                "created_at": now,
                "updated_at": now,
            }
            for row in all_actions
        ],
    )

    print(
        f"✅ Seeded company '{company_name}' "
        f"(id={company_id}, super_user_id={super_user_id}, dept_id={department_id})"
    )

    return {
        "company_id":         company_id,
        "department_id":      department_id,
        "super_admin_role_id": super_admin_role_id,
        "regular_role_id":    regular_role_id,
        "super_user_id":      super_user_id,
        "regular_user_id":    regular_user_id,
    }


# ---------------------------------------------------------------------------
# Script entry-point: seed Administrator + Company A (Datagrid)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    session = Session()

    t = metadata.tables

    # --- 1. Seed the single platform Administrator ---
    existing = session.execute(t["administrators"].select()).fetchone()
    if existing:
        print(f"⚠️  Administrator already exists ({existing.email}) — skipping.")
    else:
        admin_email    = input("Administrator email: ").strip()
        admin_name     = input("Administrator name: ").strip()
        admin_password = getpass.getpass("Administrator password: ")
        session.execute(
            t["administrators"].insert().values(
                name=admin_name,
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status=1,
            )
        )
        print(f"✅ Administrator '{admin_email}' created.")

    # --- 2. Seed Company A (Datagrid) ---
    seed_company(
        session,
        company_name="Datagrid",
        super_admin_email="rushiraj@datagrid.co.in",
        super_admin_password="admin123",
        super_admin_name="Rushiraj",
        regular_admin_email="john@datagrid.co.in",
        regular_admin_password="admin123",
        regular_admin_name="John Admin",
    )

    session.commit()
    session.close()
    print("✅ Seeding complete.")
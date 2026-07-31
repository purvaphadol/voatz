"""
seed_data.py — Production-ready seed script for the Voatz platform.

Seeds:
1. Initial Platform Administrator account (SaaS Product Owner)
2. Master System Modules Catalog (system_modules & system_module_actions)

Idempotent: Skips records if already present in database to prevent duplication.
Exposes helper seed_company() for automated test runs & onboarding pipelines.
"""

import os
import re
import getpass
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

load_dotenv()

DATABASE_URI = os.environ.get("DATABASE_URL")
if not DATABASE_URI:
    print("❌ ERROR: DATABASE_URL environment variable is not set.")
    exit(1)

masked_uri = re.sub(r':([^@]+)@', ':****@', DATABASE_URI)
print(f"Connecting to database: {masked_uri}")

engine = create_engine(DATABASE_URI)
metadata = MetaData()
metadata.reflect(bind=engine)
Session = sessionmaker(bind=engine)

SYSTEM_MODULE_SPECS = [
    ("Dashboard",           "dashboard",           "home",          1),
    ("Users",               "users",               "users",         2),
    ("Roles",               "roles",               "shield",        3),
    ("Departments",         "departments",         "briefcase",     4),
    ("Companies",           "companies",           "building",      5),
    ("Modules",             "modules",             "box",           6),
    ("Permissions",         "permissions",         "lock",          7),
    ("UserRoles",           "user-roles",          "user-check",    8),
    ("Settings",            "settings",            "settings",      9),
    ("Voters",              "voters",              "user-check",   10),
    ("Elections",           "elections",           "vote",         11),
    ("Ballots",             "ballots",             "file-text",    12),
    ("Candidates",          "candidates",          "user",         13),
    ("Votes",               "votes",               "check-square", 14),
    ("VoterRegistrations",  "voter-registrations", "clipboard-list",15),
    ("AuditLogs",           "audit-logs",          "activity",     16),
]

MODULE_NAMES = [name for name, _, _, _ in SYSTEM_MODULE_SPECS]

ACTIONS = [
    {"name": "view",   "url": "/view"},
    {"name": "create", "url": "/create"},
    {"name": "update", "url": "/update"},
    {"name": "delete", "url": "/delete"},
]


def seed_administrator(session):
    """Seed the initial Platform Administrator account if none exists."""
    t = metadata.tables
    if "administrators" not in t:
        print("❌ Table 'administrators' does not exist in schema. Please run migrations first.")
        return

    existing = session.execute(t["administrators"].select()).fetchone()
    if existing:
        print(f"ℹ️  Platform Administrator already exists ({existing.email}) — skipping creation.")
        return existing.email

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@gmail.com").strip()
    admin_name = os.environ.get("ADMIN_NAME", "Platform Administrator").strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")

    now = datetime.now(timezone.utc)
    session.execute(
        t["administrators"].insert().values(
            name=admin_name,
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            created_at=now,
            updated_at=now,
            status=1,
        )
    )
    session.commit()
    print(f"✅ Platform Administrator '{admin_email}' successfully created.")
    return admin_email


def seed_system_modules(session):
    """Seed base SystemModules and SystemModuleActions if not present."""
    t = metadata.tables
    if "system_modules" not in t or "system_module_actions" not in t:
        print("❌ System modules tables do not exist in schema. Please run migrations first.")
        return

    now = datetime.now(timezone.utc)
    seeded_count = 0

    for name, route, icon, order in SYSTEM_MODULE_SPECS:
        existing = session.execute(
            t["system_modules"].select().where(t["system_modules"].c.module_name == name)
        ).fetchone()

        if existing:
            mod_id = existing.id
        else:
            mod_id = session.execute(
                t["system_modules"].insert().values(
                    module_name=name,
                    route_name=route,
                    icon=icon,
                    order_index=order,
                    status=1,
                    created_at=now,
                    updated_at=now,
                ).returning(t["system_modules"].c.id)
            ).scalar()
            seeded_count += 1

        # Seed 4 standard actions for this module
        for act in ACTIONS:
            act_existing = session.execute(
                t["system_module_actions"].select().where(
                    t["system_module_actions"].c.system_module_id == mod_id,
                    t["system_module_actions"].c.action_name == act["name"]
                )
            ).fetchone()

            if not act_existing:
                session.execute(
                    t["system_module_actions"].insert().values(
                        system_module_id=mod_id,
                        action_name=act["name"],
                        action_url=act["url"],
                        status=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

    session.commit()
    if seeded_count > 0:
        print(f"✅ Seeded {seeded_count} new Master System Modules into global catalog.")
    else:
        print("ℹ️  Master System Modules already seeded — skipping creation.")


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
    """Seed a complete company for testing/onboarding pipelines."""
    t = metadata.tables
    now = datetime.now(timezone.utc)

    # 1. Company
    company_id = session.execute(
        t["companies"].insert().values(
            company_name=company_name,
            created_at=now,
            updated_at=now,
            status=1,
        ).returning(t["companies"].c.id)
    ).scalar()

    # 2. Provision SystemModules to company_modules
    all_sys_mods = session.execute(t["system_modules"].select()).fetchall()
    if all_sys_mods:
        session.execute(
            t["company_modules"].insert(),
            [
                {
                    "company_id": company_id,
                    "system_module_id": mod.id,
                    "status": 1,
                    "created_at": now,
                    "updated_at": now,
                }
                for mod in all_sys_mods
            ]
        )

    # 3. Department
    department_id = session.execute(
        t["departments"].insert().values(
            department_name="Admin",
            company_id=company_id,
            created_at=now,
            updated_at=now,
            status=1,
        ).returning(t["departments"].c.id)
    ).scalar()

    # 4. Super Admin role
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

    # Regular Admin role
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

    # 5. Super admin user
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

    # 6. Legacy module rows for backward compatibility
    module_rows = [
        {
            "module_name": mod.module_name,
            "route_name": mod.route_name,
            "icon": mod.icon,
            "order_index": mod.order_index,
            "company_id": company_id,
            "status": 1,
            "created_at": now,
            "updated_at": now,
        }
        for mod in all_sys_mods
    ]
    if module_rows:
        module_ids = session.execute(
            t["modules"].insert().returning(t["modules"].c.id),
            module_rows,
        ).scalars().all()

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

    return {
        "company_id": company_id,
        "department_id": department_id,
        "super_admin_role_id": super_admin_role_id,
        "regular_role_id": regular_role_id,
        "super_user_id": super_user_id,
        "regular_user_id": regular_user_id,
    }


if __name__ == "__main__":
    session = Session()
    try:
        print("\n--- Seeding Production Base Data ---")
        seed_administrator(session)
        seed_system_modules(session)
        print("✅ Seeding process completed successfully.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error during seeding: {e}")
    finally:
        session.close()
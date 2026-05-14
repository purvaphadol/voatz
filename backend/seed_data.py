from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from datetime import datetime

# DB config (note: %40 is URL encoded '@')
DATABASE_URI = "postgresql://flask_user:REDACTED@localhost/voatz"
engine = create_engine(DATABASE_URI)
metadata = MetaData()
metadata.reflect(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

# Table references
company = metadata.tables['companies']
department = metadata.tables['departments']
role = metadata.tables['roles']
user = metadata.tables['users']
module = metadata.tables['modules']
module_action = metadata.tables['module_action']
role_permission = metadata.tables['role_permission_mapping']
user_role_mapping = metadata.tables['user_role_mapping']

# Insert Company
company_id = session.execute(company.insert().values(
    company_name='Datagrid',
    created_at=datetime.now(),
    updated_at=datetime.now()
).returning(company.c.id)).scalar()

# Insert Department
department_id = session.execute(department.insert().values(
    department_name='Admin',
    company_id=company_id,
    created_at=datetime.now(),
    updated_at=datetime.now()
).returning(department.c.id)).scalar()

# Insert Roles
super_admin_id = session.execute(role.insert().values(
    role_name='Super Admin',
    department_id=department_id,
    company_id=company_id,
    created_at=datetime.now(),
    updated_at=datetime.now()
).returning(role.c.id)).scalar()

admin_id = session.execute(role.insert().values(
    role_name='Admin',
    department_id=department_id,
    company_id=company_id,
    created_at=datetime.now(),
    updated_at=datetime.now()
).returning(role.c.id)).scalar()

# Insert Users
user_1_id = session.execute(user.insert().values(
    name="Rushiraj",
    email="rushiraj@datagrid.co.in",
    password_hash=generate_password_hash("admin123"),
    company_id=company_id,
    created_at=datetime.now(),
    updated_at=datetime.now()
).returning(user.c.id)).scalar()

user_2_id = session.execute(user.insert().values(
    name="John Admin",
    email="john@datagrid.co.in",
    password_hash=generate_password_hash("admin123"),
    company_id=company_id,
    created_at=datetime.now(),
    updated_at=datetime.now()
).returning(user.c.id)).scalar()

# Insert User-Role Mappings
session.execute(user_role_mapping.insert().values([
    {
        "user_id": user_1_id,
        "role_id": super_admin_id,
        "department_id": department_id,
        "company_id": company_id,
        "status": 1
    },
    {
        "user_id": user_2_id,
        "role_id": admin_id,
        "department_id": department_id,
        "company_id": company_id,
        "status": 1
    }
]))

# Insert Modules
modules = [
    {"module_name": "Dashboard", "company_id": company_id, "is_active": True, "order_index": 1},
    {"module_name": "Users", "company_id": company_id, "is_active": True, "order_index": 2},
    {"module_name": "Roles", "company_id": company_id, "is_active": True, "order_index": 3},
    {"module_name": "Departments", "company_id": company_id, "is_active": True, "order_index": 4},
    {"module_name": "Companies", "company_id": company_id, "is_active": True, "order_index": 5},
    {"module_name": "Modules", "company_id": company_id, "is_active": True, "order_index": 6},
    {"module_name": "Permissions", "company_id": company_id, "is_active": True, "order_index": 7},
    {"module_name": "UserRoles", "company_id": company_id, "is_active": True, "order_index": 8},
    {"module_name": "Settings", "company_id": company_id, "is_active": True, "order_index": 9},
    # Voting system modules
    {"module_name": "Voters", "company_id": company_id, "is_active": True, "order_index": 10},
    {"module_name": "Elections", "company_id": company_id, "is_active": True, "order_index": 11},
    {"module_name": "Ballots", "company_id": company_id, "is_active": True, "order_index": 12},
    {"module_name": "Candidates", "company_id": company_id, "is_active": True, "order_index": 13},
    {"module_name": "Votes", "company_id": company_id, "is_active": True, "order_index": 14},
    {"module_name": "VoterRegistrations", "company_id": company_id, "is_active": True, "order_index": 15}
]

for m in modules:
    m["created_at"] = m["updated_at"] = datetime.now()

module_ids = session.execute(module.insert().returning(module.c.id), modules).scalars().all()

# Insert Module Actions
actions = [
    {'name': 'view', 'url': '/view'},
    {'name': 'create', 'url': '/create'},
    {'name': 'update', 'url': '/update'},
    {'name': 'delete', 'url': '/delete'}
]
module_action_rows = []

for mod_id in module_ids:
    for act in actions:
        module_action_rows.append({
            "module_id": mod_id,
            "action_name": act['name'],
            "action_url": act['url'],
            "company_id": company_id,
            "status": 1
        })

session.execute(module_action.insert(), module_action_rows)

# Assign permissions to Super Admin (get all module actions for this company)
all_actions = session.execute(
    module_action.select().where(module_action.c.company_id == company_id)
).fetchall()

session.execute(role_permission.insert(), [{
    "company_id": company_id,
    "role_id": super_admin_id,
    "module_id": row.module_id,
    "action_id": row.id
} for row in all_actions])

session.commit()
session.close()
print("✅ Seeding complete.")
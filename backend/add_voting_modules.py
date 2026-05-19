from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# DB config
import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URI = os.environ["DATABASE_URL"]  # no fallback — fails loud if not set

engine = create_engine(DATABASE_URI)
metadata = MetaData()
metadata.reflect(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

# Table references
company = metadata.tables['companies']
module = metadata.tables['modules']
module_action = metadata.tables['module_action']
role_permission = metadata.tables['role_permission_mapping']
role = metadata.tables['roles']

# Get existing company
company_row = session.execute(company.select().where(company.c.company_name == 'Datagrid')).first()
if not company_row:
    print("❌ Company 'Datagrid' not found")
    exit(1)

company_id = company_row.id
print(f"✅ Found company 'Datagrid' with ID: {company_id}")

# Get Super Admin role
super_admin_row = session.execute(
    role.select().where(role.c.role_name == 'Super Admin').where(role.c.company_id == company_id)
).first()

if not super_admin_row:
    print("❌ Super Admin role not found")
    exit(1)

super_admin_id = super_admin_row.id
print(f"✅ Found Super Admin role with ID: {super_admin_id}")

# Check if voting modules already exist
existing_modules = session.execute(
    module.select().where(module.c.company_id == company_id)
).fetchall()

existing_module_names = [mod.module_name for mod in existing_modules]
print(f"Existing modules: {existing_module_names}")

# New voting system modules
voting_modules = [
    {"module_name": "Voters", "company_id": company_id, "is_active": True, "order_index": 10},
    {"module_name": "Elections", "company_id": company_id, "is_active": True, "order_index": 11},
    {"module_name": "Ballots", "company_id": company_id, "is_active": True, "order_index": 12},
    {"module_name": "Candidates", "company_id": company_id, "is_active": True, "order_index": 13},
    {"module_name": "Votes", "company_id": company_id, "is_active": True, "order_index": 14},
    {"module_name": "VoterRegistrations", "company_id": company_id, "is_active": True, "order_index": 15}
]

# Insert only new modules
new_modules_to_insert = []
for mod in voting_modules:
    if mod["module_name"] not in existing_module_names:
        mod["created_at"] = mod["updated_at"] = datetime.now()
        new_modules_to_insert.append(mod)

if new_modules_to_insert:
    print(f"Adding {len(new_modules_to_insert)} new voting modules...")
    module_ids = session.execute(module.insert().returning(module.c.id), new_modules_to_insert).scalars().all()
    
    # Insert Module Actions for new modules
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
    
    # Get all new module actions
    new_actions = session.execute(
        module_action.select().where(module_action.c.module_id.in_(module_ids))
    ).fetchall()
    
    # Assign permissions to Super Admin
    session.execute(role_permission.insert(), [{
        "company_id": company_id,
        "role_id": super_admin_id,
        "module_id": row.module_id,
        "action_id": row.id
    } for row in new_actions])
    
    session.commit()
    print(f"✅ Added {len(new_modules_to_insert)} voting modules with permissions")
else:
    print("✅ All voting modules already exist")

session.close()
print("✅ Voting modules setup complete") 
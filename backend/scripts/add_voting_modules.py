from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URI = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URI)
metadata = MetaData()
metadata.reflect(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

company = metadata.tables['companies']
sys_module = metadata.tables['system_modules']
sys_action = metadata.tables['system_module_actions']
comp_module = metadata.tables['company_modules']
role_permission = metadata.tables['role_permission_mapping']
role = metadata.tables['roles']

company_row = session.execute(company.select().where(company.c.company_name == 'Datagrid')).first()
if not company_row:
    print("❌ Company 'Datagrid' not found")
    exit(1)

company_id = company_row.id
print(f"✅ Found company 'Datagrid' with ID: {company_id}")

super_admin_row = session.execute(
    role.select().where(role.c.role_name == 'Super Admin').where(role.c.company_id == company_id)
).first()

if not super_admin_row:
    print("❌ Super Admin role not found")
    exit(1)

super_admin_id = super_admin_row.id
print(f"✅ Found Super Admin role with ID: {super_admin_id}")

voting_modules_data = [
    {"module_name": "Voters", "order_index": 10},
    {"module_name": "Elections", "order_index": 11},
    {"module_name": "Ballots", "order_index": 12},
    {"module_name": "Candidates", "order_index": 13},
    {"module_name": "Votes", "order_index": 14},
    {"module_name": "VoterRegistrations", "order_index": 15}
]

actions_def = [
    {'name': 'view', 'url': '/view'},
    {'name': 'create', 'url': '/create'},
    {'name': 'update', 'url': '/update'},
    {'name': 'delete', 'url': '/delete'}
]

for mod_data in voting_modules_data:
    mod_name = mod_data["module_name"]
    order_idx = mod_data["order_index"]

    sys_mod = session.execute(sys_module.select().where(sys_module.c.module_name == mod_name)).first()
    if not sys_mod:
        res = session.execute(sys_module.insert().returning(sys_module.c.id), [{
            "module_name": mod_name,
            "order_index": order_idx,
            "status": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }])
        sys_mod_id = res.scalar()
        print(f"✅ Created system module '{mod_name}' (ID: {sys_mod_id})")
    else:
        sys_mod_id = sys_mod.id

    cm = session.execute(
        comp_module.select().where(comp_module.c.company_id == company_id).where(comp_module.c.system_module_id == sys_mod_id)
    ).first()

    if not cm:
        session.execute(comp_module.insert(), [{
            "company_id": company_id,
            "system_module_id": sys_mod_id,
            "status": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }])
        print(f"✅ Provisioned '{mod_name}' for company {company_id}")

    for act in actions_def:
        act_row = session.execute(
            sys_action.select().where(sys_action.c.system_module_id == sys_mod_id).where(sys_action.c.action_name == act['name'])
        ).first()

        if not act_row:
            act_res = session.execute(sys_action.insert().returning(sys_action.c.id), [{
                "system_module_id": sys_mod_id,
                "action_name": act['name'],
                "action_url": act['url'],
                "status": 1,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }])
            act_id = act_res.scalar()
        else:
            act_id = act_row.id

        rp = session.execute(
            role_permission.select()
            .where(role_permission.c.role_id == super_admin_id)
            .where(role_permission.c.module_id == sys_mod_id)
            .where(role_permission.c.action_id == act_id)
            .where(role_permission.c.company_id == company_id)
        ).first()

        if not rp:
            session.execute(role_permission.insert(), [{
                "company_id": company_id,
                "role_id": super_admin_id,
                "module_id": sys_mod_id,
                "action_id": act_id,
                "status": 1,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }])

session.commit()
session.close()
print("✅ Voting modules setup complete in system_modules catalog")
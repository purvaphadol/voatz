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

sys_module = metadata.tables['system_modules']
sys_action = metadata.tables['system_module_actions']

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
            print(f"  ✅ Added action '{act['name']}' to '{mod_name}'")

session.commit()
session.close()
print("✅ Voting modules catalog setup complete in system_modules")
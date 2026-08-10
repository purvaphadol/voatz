import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def run_migrations():
    app = create_app()
    with app.app_context():
        print("Starting RBAC database schema migration...")
        
        # Get existing table names
        inspector = db.inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        print(f"Existing database tables: {existing_tables}")
        
        # 1. Add code column to system_modules if it exists
        if 'system_modules' in existing_tables:
            print("Adding 'code' column to system_modules...")
            db.session.execute(text("""
                ALTER TABLE system_modules 
                ADD COLUMN IF NOT EXISTS code VARCHAR(50);
            """))
            db.session.commit()

        # 2. Add status column to user role table (user_roles or user_role_mappings)
        user_role_tbl = 'user_roles' if 'user_roles' in existing_tables else ('user_role_mappings' if 'user_role_mappings' in existing_tables else None)
        if user_role_tbl:
            print(f"Adding 'status' column to {user_role_tbl}...")
            db.session.execute(text(f"""
                ALTER TABLE {user_role_tbl} 
                ADD COLUMN IF NOT EXISTS status INTEGER DEFAULT 1;
            """))
            db.session.commit()
        
        # 3. Populate default code values for existing system_modules based on route_name or module_name
        print("Populating 'code' column for existing system_modules...")
        from app.models.module import SystemModule
        modules = SystemModule.query.all()
        for mod in modules:
            if not mod.code:
                # Generate canonical code from route_name or module_name
                raw = mod.route_name or mod.module_name or f"module_{mod.id}"
                clean_code = raw.lower().replace(' ', '_').replace('-', '_')
                mod.code = clean_code
                print(f"  Updated module ID {mod.id} ({mod.module_name}) -> code: '{clean_code}'")
        
        db.session.commit()
        
        # 4. Add unique constraints if they don't exist
        print("Ensuring composite unique constraints on junction tables...")
        possible_constraints = [
            ("role_permission_mappings", "uq_role_module_action_company", "UNIQUE (role_id, module_id, action_id, company_id)"),
            ("role_permissions", "uq_role_module_action_company", "UNIQUE (role_id, module_id, action_id, company_id)"),
            ("user_permission_mappings", "uq_user_module_action_company", "UNIQUE (user_id, module_id, action_id, company_id)"),
            ("user_permissions", "uq_user_module_action_company", "UNIQUE (user_id, module_id, action_id, company_id)"),
            ("user_role_mappings", "uq_user_role_dept_company", "UNIQUE (user_id, role_id, department_id, company_id)"),
            ("user_roles", "uq_user_role_dept_company", "UNIQUE (user_id, role_id, department_id, company_id)")
        ]
        
        for table, c_name, c_sql in possible_constraints:
            if table in existing_tables:
                try:
                    db.session.execute(text(f"""
                        DO $$ 
                        BEGIN 
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint WHERE conname = '{c_name}'
                            ) THEN
                                ALTER TABLE {table} ADD CONSTRAINT {c_name} {c_sql};
                            END IF;
                        END $$;
                    """))
                    db.session.commit()
                    print(f"  Constraint '{c_name}' on table '{table}' verified/created.")
                except Exception as e:
                    db.session.rollback()
                    print(f"  Warning: Could not create constraint '{c_name}' on '{table}': {e}")
                
        print("Migration completed successfully!")

if __name__ == '__main__':
    run_migrations()

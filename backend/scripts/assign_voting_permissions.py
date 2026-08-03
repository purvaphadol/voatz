#!/usr/bin/env python3
"""
Script to assign voting module permissions to Super Admin role using SystemModule catalog
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Role, SystemModule, SystemModuleAction, CompanyModule, RolePermissionMapping, Company

def assign_voting_permissions():
    """Assign all voting module permissions to Super Admin role"""
    app = create_app()
    
    with app.app_context():
        print("🔐 Assigning voting module permissions...")
        
        # Get the company
        company = Company.query.first()
        if not company:
            print("❌ No company found")
            return
        
        print(f"✅ Found company '{company.company_name}' with ID: {company.id}")
        
        # Get Super Admin role
        super_admin_role = Role.query.filter_by(
            role_name='Super Admin', 
            company_id=company.id
        ).first()
        
        if not super_admin_role:
            print("❌ Super Admin role not found")
            return
        
        print(f"✅ Found Super Admin role with ID: {super_admin_role.id}")
        
        # Voting modules to assign permissions for
        voting_modules = [
            'Voters',
            'Elections', 
            'Ballots',
            'Candidates',
            'Votes',
            'VoterRegistrations'
        ]
        
        total_assigned = 0
        
        for module_name in voting_modules:
            print(f"\n📋 Processing module: {module_name}")
            
            # Get the system module
            module = SystemModule.query.filter_by(module_name=module_name).first()
            if not module:
                print(f"❌ SystemModule '{module_name}' not found")
                continue
            
            print(f"✅ Found system module '{module_name}' with ID: {module.id}")
            
            # Ensure CompanyModule mapping exists
            comp_mod = CompanyModule.query.filter_by(company_id=company.id, system_module_id=module.id).first()
            if not comp_mod:
                comp_mod = CompanyModule(company_id=company.id, system_module_id=module.id, status=1)
                db.session.add(comp_mod)
                print(f"   ✅ Provisioned system module '{module_name}' to company {company.id}")
            
            # Get all actions for this system module
            module_actions = SystemModuleAction.query.filter_by(system_module_id=module.id).all()
            
            if not module_actions:
                print(f"❌ No actions found for system module '{module_name}'")
                continue
            
            print(f"✅ Found {len(module_actions)} actions for system module '{module_name}'")
            
            # Assign permissions for each action
            for action in module_actions:
                existing_permission = RolePermissionMapping.query.filter_by(
                    role_id=super_admin_role.id,
                    module_id=module.id,
                    action_id=action.id,
                    company_id=company.id
                ).first()
                
                if existing_permission:
                    print(f"   ➡️ Permission already exists: {action.action_name}")
                    continue
                
                new_permission = RolePermissionMapping(
                    role_id=super_admin_role.id,
                    module_id=module.id,
                    action_id=action.id,
                    company_id=company.id,
                    status=1
                )
                
                db.session.add(new_permission)
                total_assigned += 1
                print(f"   ✅ Assigned permission: {action.action_name}")
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\n🎉 Successfully assigned {total_assigned} voting module permissions to Super Admin role!")
            print("✅ You can now access all voting system features")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error committing changes: {str(e)}")

if __name__ == '__main__':
    assign_voting_permissions()
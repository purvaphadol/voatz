import pytest
import os
from app import create_app, db
from app.models.company import Company
from app.models.department import Department
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRoleMapping
from app.models.module import Module
from app.models.module_action import ModuleAction
from app.models.role_permission import RolePermissionMapping
from app.models.voter import Voter
from flask_jwt_extended import create_access_token
from datetime import timedelta
from werkzeug.security import generate_password_hash

# Dynamically make Voter.user_id nullable for testing
if hasattr(Voter, 'user_id') and hasattr(Voter.user_id, 'property'):
    Voter.user_id.property.columns[0].nullable = True


@pytest.fixture(scope='session')
def app():
    test_db_url = os.environ.get('TEST_DATABASE_URL')
    if not test_db_url:
        from dotenv import load_dotenv
        load_dotenv()
        db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/voatz')
        # if the URL already has _test, don't add it again
        if not db_url.endswith('_test'):
            test_db_url = db_url + '_test'
        else:
            test_db_url = db_url
    from config.config import Config
    Config.SQLALCHEMY_DATABASE_URI = test_db_url
    flask_app = create_app()
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': test_db_url,
        'JWT_SECRET_KEY': 'test-secret-key'
    })

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def setup_data(app):
    with app.app_context():
        db.drop_all()
        db.create_all()

        company = Company(company_name='Test Company')
        db.session.add(company)
        db.session.flush()

        dept = Department(department_name='Test Dept', company_id=company.id)
        db.session.add(dept)
        db.session.flush()

        role = Role(role_name='Super Admin', company_id=company.id, department_id=dept.id, status=1)
        db.session.add(role)
        db.session.flush()

        user = User(
            name='Test Staff',
            email='staff@test.com',
            company_id=company.id,
            department_id=dept.id,
            status=1
        )
        user.password_hash = generate_password_hash('password123')
        db.session.add(user)
        db.session.flush()

        user_role = UserRoleMapping(user_id=user.id, role_id=role.id, company_id=company.id, status=1)
        db.session.add(user_role)

        modules_data = {
            'Voters': ['view', 'create', 'update', 'delete'],
            'VoterRegistrations': ['view', 'create', 'update', 'delete'],
            'Elections': ['view', 'create', 'update', 'delete'],
        }

        for mod_name, actions in modules_data.items():
            mod = Module(module_name=mod_name, company_id=company.id)
            db.session.add(mod)
            db.session.flush()

            for act_name in actions:
                act = ModuleAction(action_name=act_name, action_url='', module_id=mod.id, company_id=company.id)
                db.session.add(act)
                db.session.flush()

                rp = RolePermissionMapping(role_id=role.id, module_id=mod.id, action_id=act.id, company_id=company.id)
                db.session.add(rp)

        db.session.commit()
        token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=1))

        company_id = company.id
        user_id = user.id

        yield {
            'company_id': company_id,
            'user_id': user_id,
            'token': token,
            'headers': {'Authorization': f'Bearer {token}'}
        }
        db.session.remove()

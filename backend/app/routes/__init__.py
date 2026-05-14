from .auth import auth_bp
from .users import users_bp
from .roles import roles_bp
from .user_roles import user_roles_bp
from .permissions import permissions_bp
from .companies import companies_bp
from .departments import departments_bp
from .modules import modules_bp
from .module_actions import module_actions_bp
from .health import health_bp
from .audit import audit_bp
from .menu import menu_bp
from .elections import elections_bp
from .ballots import ballots_bp
from .candidates import candidates_bp
from .voters import voters_bp
from .voter_registrations import voter_registrations_bp
from .votes import votes_bp
from .dashboard import dashboard_bp

def register_blueprints(app):
    """Register all blueprint routes"""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(roles_bp, url_prefix='/api/roles')
    app.register_blueprint(user_roles_bp, url_prefix='/api/user-roles')
    app.register_blueprint(permissions_bp, url_prefix='/api/permissions')
    app.register_blueprint(companies_bp, url_prefix='/api/companies')
    app.register_blueprint(departments_bp, url_prefix='/api/departments')
    app.register_blueprint(modules_bp, url_prefix='/api/modules')
    app.register_blueprint(module_actions_bp, url_prefix='/api/module-actions')
    app.register_blueprint(health_bp, url_prefix='/api/health')
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    app.register_blueprint(menu_bp, url_prefix='/api/menu')
    app.register_blueprint(elections_bp, url_prefix='/api/elections')
    app.register_blueprint(ballots_bp, url_prefix='/api/ballots')
    app.register_blueprint(candidates_bp, url_prefix='/api/candidates')
    app.register_blueprint(voters_bp, url_prefix='/api/voters')
    app.register_blueprint(voter_registrations_bp, url_prefix='/api/voter-registrations')
    app.register_blueprint(votes_bp, url_prefix='/api/votes')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

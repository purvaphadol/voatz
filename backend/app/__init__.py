from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config.config import Config
import logging
import sys
import os

from flask_sqlalchemy.query import Query

class ActiveQuery(Query):
    """Custom Query class for models with status fields.
    Automatically excludes status=9 (deactivated) records unless .with_deactivated() is called.
    """
    def with_deactivated(self):
        """Include deactivated (status=9) records in query results."""
        return self.execution_options(include_deactivated=True)

db = SQLAlchemy(query_class=ActiveQuery)
migrate = Migrate()
jwt = JWTManager()

def create_app():
    # Point static_folder to backend/static so uploaded images are served at /static/...
    _static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    app = Flask(__name__, static_folder=_static_folder, static_url_path='/static')
    app.config.from_object(Config)

    # Configure logging
    if app.config.get('DEBUG'):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('debug.log')
            ]
        )
        
        # Set specific loggers
        logging.getLogger('app.utils').setLevel(logging.INFO)
        logging.getLogger('app.routes.candidates').setLevel(logging.INFO)
        
        app.logger.info("🚀 Flask app started with debug logging enabled")

    # Enable CORS with environment-specific origins
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # JWT Error Handlers with better logging
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        app.logger.warning(f"🔒 Expired token attempt: {jwt_payload}")
        return {"error": "Token has expired", "message": "Please login again"}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        app.logger.warning(f"🔒 Invalid token: {error}")
        return {"error": "Invalid token", "message": "Please provide a valid token"}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        app.logger.warning(f"🔒 Missing token: {error}")
        return {"error": "Authorization token required", "message": "Please provide an authorization token"}, 401

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        app.logger.warning(f"🔒 Stale token: {jwt_payload}")
        return {"error": "Fresh token required", "message": "Please login again"}, 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        app.logger.warning(f"🔒 Revoked token: {jwt_payload}")
        return {"error": "Token has been revoked", "message": "Please login again"}, 401

    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.roles import roles_bp
    from app.routes.modules import modules_bp
    from app.routes.module_actions import module_actions_bp
    from app.routes.permissions import permissions_bp
    from app.routes.permissions_crud import permissions_crud_bp
    from app.routes.menu import menu_bp
    from app.routes.companies import companies_bp
    from app.routes.departments import departments_bp
    from app.routes.user_roles import user_roles_bp
    from app.routes.audit import audit_bp
    
    # Voting system blueprints
    from app.routes.voters import voters_bp
    from app.routes.elections import elections_bp
    from app.routes.ballots import ballots_bp
    from app.routes.candidates import candidates_bp
    from app.routes.votes import votes_bp
    from app.routes.voter_registrations import voter_registrations_bp
    from app.routes.dashboard import dashboard_bp

    

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(roles_bp, url_prefix='/api/roles')
    app.register_blueprint(modules_bp, url_prefix='/api/modules')
    app.register_blueprint(module_actions_bp, url_prefix='/api/module-actions')
    app.register_blueprint(permissions_bp, url_prefix='/api/permissions')
    app.register_blueprint(permissions_crud_bp, url_prefix='/api/permissions')
    app.register_blueprint(menu_bp, url_prefix='/api/menu')
    app.register_blueprint(companies_bp, url_prefix='/api/companies')
    app.register_blueprint(departments_bp, url_prefix='/api/departments')
    app.register_blueprint(user_roles_bp, url_prefix='/api/user-roles')
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    
    # Register voting system blueprints
    app.register_blueprint(voters_bp, url_prefix='/api/voters')
    app.register_blueprint(elections_bp, url_prefix='/api/elections')
    app.register_blueprint(ballots_bp, url_prefix='/api/ballots')
    app.register_blueprint(candidates_bp, url_prefix='/api/candidates')
    app.register_blueprint(votes_bp, url_prefix='/api/votes')
    app.register_blueprint(voter_registrations_bp, url_prefix='/api/voter-registrations')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    from app.routes.health import health_bp
    app.register_blueprint(health_bp)

    @app.route('/api/health')
    def health():
        return {"status": "ok"}, 200

    return app



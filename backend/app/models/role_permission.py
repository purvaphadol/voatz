from app import db
from app.models.base import TimestampAuditMixin

class RolePermissionMapping(db.Model, TimestampAuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('system_modules.id'), nullable=False)
    action_id = db.Column(db.Integer, db.ForeignKey('system_module_actions.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    status = db.Column(db.Integer, default=1)

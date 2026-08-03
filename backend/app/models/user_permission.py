from app import db
from app.models.base import TimestampAuditMixin

class UserPermissionMapping(db.Model, TimestampAuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    module_id = db.Column(db.Integer, db.ForeignKey('system_modules.id'), nullable=False)
    action_id = db.Column(db.Integer, db.ForeignKey('system_module_actions.id'), nullable=False)
    permission_type = db.Column(db.Integer, default=1)  # 1 allow, 0 deny
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    status = db.Column(db.Integer, default=1)

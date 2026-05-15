from app import db
from app.models.base import TimestampAuditMixin

class UserPermissionMapping(db.Model, TimestampAuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'))
    action_id = db.Column(db.Integer, db.ForeignKey('module_action.id'))
    permission_type = db.Column(db.Integer)  # 1 allow, 0 deny
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))

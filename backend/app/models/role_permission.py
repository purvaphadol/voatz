from app import db
from app.models.base import TimestampAuditMixin

class RolePermissionMapping(db.Model, TimestampAuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'))
    action_id = db.Column(db.Integer, db.ForeignKey('module_action.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))

from app import db
from app.models.base import TimestampAuditMixin

class ModuleAction(db.Model, TimestampAuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    action_name = db.Column(db.String(100), nullable=False)
    action_url = db.Column(db.String(255), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
 

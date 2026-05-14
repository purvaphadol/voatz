from app import db
from app.models.base import TimestampAuditMixin
from datetime import datetime

class AuditLog(db.Model, TimestampAuditMixin):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Action details
    action = db.Column(db.String(50), nullable=False)  # login, create_user, update_role, etc.
    module = db.Column(db.String(50), nullable=True)   # Users, Roles, Settings, etc.
    target_type = db.Column(db.String(50), nullable=True)  # user, role, department, etc.
    target_id = db.Column(db.Integer, nullable=True)   # ID of the target object
    
    # Context
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Request details
    method = db.Column(db.String(10), nullable=True)   # GET, POST, PUT, DELETE
    endpoint = db.Column(db.String(200), nullable=True)
    
    # Result
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Additional data (JSON) - renamed from 'metadata' to avoid SQLAlchemy conflict
    extra_data = db.Column(db.JSON, nullable=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id} at {self.created_at}>' 
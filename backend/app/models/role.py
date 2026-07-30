from app import db
from app.models.base import TimestampAuditMixin

class Role(db.Model, TimestampAuditMixin):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    department_id    = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    is_super_admin   = db.Column(db.Boolean, nullable=False, default=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Relationships
    department = db.relationship('Department', backref='roles')
    company = db.relationship('Company', backref='roles')
    
    # Unique constraint: role name should be unique within a department
    __table_args__ = (
        db.UniqueConstraint('role_name', 'department_id', name='unique_role_per_department'),
    )

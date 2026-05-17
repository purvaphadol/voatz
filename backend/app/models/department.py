from app import db
from app.models.base import TimestampAuditMixin

class Department(db.Model, TimestampAuditMixin):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Relationships
    company = db.relationship('Company', backref='departments')

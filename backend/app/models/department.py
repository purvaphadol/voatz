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
    
    # Unique constraint: department name should be unique within a company
    __table_args__ = (
        db.UniqueConstraint('department_name', 'company_id', name='unique_department_per_company'),
    )

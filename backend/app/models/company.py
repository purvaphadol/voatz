from app import db
from app.models.base import TimestampAuditMixin

class Company(db.Model, TimestampAuditMixin):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), unique=True, nullable=False)

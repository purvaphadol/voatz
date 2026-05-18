from app import db
from app.models.base import TimestampAuditMixin

class Company(db.Model, TimestampAuditMixin):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    address = db.Column(db.Text, nullable=True)
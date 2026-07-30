from app import db
from app.models.base import TimestampAuditMixin


class Administrator(db.Model, TimestampAuditMixin):
    __tablename__ = 'administrators'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

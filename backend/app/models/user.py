from app import db
from app.models.base import TimestampAuditMixin
from datetime import datetime, timedelta
import secrets
import string

class User(db.Model, TimestampAuditMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    # Password reset fields
    password_reset_token = db.Column(db.String(64), nullable=True, index=True)
    password_reset_expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    company = db.relationship('Company', backref='users')

    def generate_reset_token(self, expires_in_minutes: int = 30) -> str:
        """Generate a secure password reset token valid for `expires_in_minutes`."""
        token = secrets.token_urlsafe(32)
        self.password_reset_token = token
        self.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        return token

    def verify_reset_token(self, token: str) -> bool:
        """Return True if the token matches and has not expired."""
        if not self.password_reset_token or not self.password_reset_expires_at:
            return False
        if self.password_reset_token != token:
            return False
        return datetime.utcnow() < self.password_reset_expires_at

    def clear_reset_token(self):
        """Invalidate the reset token after use."""
        self.password_reset_token = None
        self.password_reset_expires_at = None

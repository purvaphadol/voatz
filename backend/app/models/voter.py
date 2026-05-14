from app import db
from app.models.base import TimestampAuditMixin

class Voter(db.Model, TimestampAuditMixin):
    __tablename__ = 'voters'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Voter identification
    voter_id = db.Column(db.String(100), unique=True, nullable=False)  # Unique voter identifier
    phone_number = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    
    # Verification status
    is_verified = db.Column(db.Boolean, default=False)
    verification_level = db.Column(db.String(20), default='none')  # none, phone, identity, biometric, full
    phone_verified_at = db.Column(db.DateTime, nullable=True)
    identity_verified_at = db.Column(db.DateTime, nullable=True)
    biometric_verified_at = db.Column(db.DateTime, nullable=True)
    
    # Biometric data (hashed for security)
    biometric_hash = db.Column(db.String(255), nullable=True)
    face_encoding_hash = db.Column(db.String(255), nullable=True)
    
    # Device and security
    registered_device_id = db.Column(db.String(255), nullable=True)
    device_fingerprint = db.Column(db.Text, nullable=True)  # JSON of device characteristics
    
    # Location and eligibility
    registered_address = db.Column(db.Text, nullable=True)
    jurisdiction = db.Column(db.String(100), nullable=True)
    voter_type = db.Column(db.String(50), default='standard')  # standard, overseas, military, disabled
    
    # Security settings
    two_factor_enabled = db.Column(db.Boolean, default=False)
    security_pin_hash = db.Column(db.String(255), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='voter_profile')
    company = db.relationship('Company', backref='voters')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('voter_id', 'company_id', name='unique_voter_per_company'),
        db.Index('idx_voter_phone', 'phone_number'),
        db.Index('idx_voter_verification', 'is_verified', 'verification_level'),
    )
    
    def __repr__(self):
        return f'<Voter {self.voter_id} - {self.user.name if self.user else "Unknown"}>' 
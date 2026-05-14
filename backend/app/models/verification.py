from app import db
from app.models.base import TimestampAuditMixin
from datetime import datetime

class Verification(db.Model, TimestampAuditMixin):
    __tablename__ = 'verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voters.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Verification identification
    verification_id = db.Column(db.String(100), unique=True, nullable=False)
    
    # Verification type and method
    verification_type = db.Column(db.String(50), nullable=False)  # phone, identity, biometric, address, manual
    verification_method = db.Column(db.String(50), nullable=True)  # sms, id_scan, facial_recognition, fingerprint
    
    # Verification data (stored securely)
    verification_data = db.Column(db.JSON, nullable=True)  # Depends on verification type
    verification_hash = db.Column(db.String(255), nullable=True)  # Hash of verification data
    document_type = db.Column(db.String(50), nullable=True)  # drivers_license, passport, id_card
    
    # Identity document information (if applicable)
    document_number = db.Column(db.String(100), nullable=True)  # Hashed/encrypted document number
    document_expiry = db.Column(db.Date, nullable=True)
    document_issuer = db.Column(db.String(100), nullable=True)  # State, country, etc.
    
    # Biometric verification details
    biometric_type = db.Column(db.String(50), nullable=True)  # fingerprint, facial, voice, iris
    biometric_quality_score = db.Column(db.Float, nullable=True)  # Quality score 0-1
    biometric_confidence_score = db.Column(db.Float, nullable=True)  # Confidence score 0-1
    
    # Phone verification details
    phone_number = db.Column(db.String(20), nullable=True)
    verification_code = db.Column(db.String(10), nullable=True)  # SMS/voice code (hashed)
    code_attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=3)
    
    # Processing and status
    status = db.Column(db.String(20), default='pending')  # pending, verified, rejected, expired, failed
    verification_score = db.Column(db.Float, nullable=True)  # Overall verification score 0-1
    confidence_level = db.Column(db.String(20), nullable=True)  # low, medium, high, very_high
    
    # Timing information
    initiated_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Processing details
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Manual verification
    verification_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.String(200), nullable=True)
    
    # Third-party verification
    external_verification_id = db.Column(db.String(100), nullable=True)  # Third-party service ID
    external_service = db.Column(db.String(50), nullable=True)  # Jumio, Onfido, etc.
    external_response = db.Column(db.JSON, nullable=True)  # Third-party response data
    
    # Device and session information
    device_id = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    location_data = db.Column(db.JSON, nullable=True)
    
    # Security and fraud detection
    fraud_check_score = db.Column(db.Float, nullable=True)  # Fraud detection score 0-1
    risk_level = db.Column(db.String(20), nullable=True)  # low, medium, high, critical
    fraud_indicators = db.Column(db.JSON, nullable=True)  # Array of fraud indicators
    
    # Compliance and audit
    compliance_checks = db.Column(db.JSON, nullable=True)  # Array of compliance check results
    audit_trail = db.Column(db.JSON, nullable=True)  # Array of audit events
    retention_period = db.Column(db.Integer, nullable=True)  # Days to retain data
    
    # Error handling
    error_count = db.Column(db.Integer, default=0)
    error_messages = db.Column(db.JSON, nullable=True)
    last_error = db.Column(db.String(500), nullable=True)
    
    # Relationships
    voter = db.relationship('Voter', backref='verifications')
    company = db.relationship('Company', backref='verifications')
    verifier = db.relationship('User', backref='verifications_performed')
    
    # Constraints and indexes
    __table_args__ = (
        db.Index('idx_verification_voter', 'voter_id', 'verification_type'),
        db.Index('idx_verification_status', 'status', 'verification_type'),
        db.Index('idx_verification_timestamp', 'initiated_at', 'verified_at'),
        db.Index('idx_verification_external', 'external_service', 'external_verification_id'),
        db.Index('idx_verification_phone', 'phone_number'),
    )
    
    def __repr__(self):
        return f'<Verification {self.verification_type} - {self.status}>'
    
    @property
    def is_verified(self):
        """Check if verification is successfully completed"""
        return self.status == 'verified'
    
    @property
    def is_expired(self):
        """Check if verification has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_pending(self):
        """Check if verification is still pending"""
        return self.status == 'pending' and not self.is_expired
    
    @property
    def verification_age_days(self):
        """Get age of verification in days"""
        if not self.verified_at:
            return None
        return (datetime.utcnow() - self.verified_at).days
    
    def generate_verification_id(self):
        """Generate unique verification ID"""
        import secrets
        import string
        alphabet = string.ascii_uppercase + string.digits
        self.verification_id = f"VER-{''.join(secrets.choice(alphabet) for _ in range(12))}"
        return self.verification_id
    
    def add_audit_event(self, event_type, description, additional_data=None):
        """Add an event to the audit trail"""
        if not self.audit_trail:
            self.audit_trail = []
        
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'description': description,
            'additional_data': additional_data or {}
        }
        self.audit_trail.append(event)
    
    def mark_verified(self, verified_by_user_id=None, notes=None):
        """Mark verification as verified"""
        self.status = 'verified'
        self.verified_at = datetime.utcnow()
        self.verified_by = verified_by_user_id
        if notes:
            self.verification_notes = notes
        self.add_audit_event('verified', 'Verification marked as verified')
    
    def mark_rejected(self, reason, rejected_by_user_id=None):
        """Mark verification as rejected"""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.verified_by = rejected_by_user_id
        self.add_audit_event('rejected', f'Verification rejected: {reason}')
    
    def increment_attempts(self):
        """Increment verification attempts"""
        self.code_attempts += 1
        if self.code_attempts >= self.max_attempts:
            self.status = 'failed'
            self.add_audit_event('failed', 'Maximum verification attempts exceeded')
    
    def get_verification_summary(self):
        """Get a summary of verification details"""
        return {
            'id': self.verification_id,
            'type': self.verification_type,
            'method': self.verification_method,
            'status': self.status,
            'score': self.verification_score,
            'confidence': self.confidence_level,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'age_days': self.verification_age_days
        } 
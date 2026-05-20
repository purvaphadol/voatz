from app import db
from app.models.base import TimestampAuditMixin
from datetime import datetime, timezone

class VoterRegistration(db.Model, TimestampAuditMixin):
    __tablename__ = 'voter_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voters.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Registration identification
    registration_id = db.Column(db.String(100), unique=True, nullable=False)
    
    # Registration status and processing
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, expired, cancelled
    registration_type = db.Column(db.String(50), default='standard')  # standard, overseas, military, early, absentee
    
    # Registration timing
    registered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Processing details
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin who processed
    approval_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.String(200), nullable=True)
    
    # Eligibility and verification
    eligibility_verified = db.Column(db.Boolean, default=False)
    identity_verified = db.Column(db.Boolean, default=False)
    address_verified = db.Column(db.Boolean, default=False)
    age_verified = db.Column(db.Boolean, default=False)
    
    # Verification requirements met
    verification_level_met = db.Column(db.String(20), default='none')  # none, basic, standard, full
    required_verification_level = db.Column(db.String(20), default='standard')
    
    # Geographic and jurisdictional eligibility
    registered_address = db.Column(db.Text, nullable=True)
    jurisdiction = db.Column(db.String(100), nullable=True)
    precinct = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    
    # Ballot access and restrictions
    eligible_ballot_types = db.Column(db.JSON, nullable=True)  # Array of ballot types voter can access
    ballot_restrictions = db.Column(db.JSON, nullable=True)  # Array of restrictions
    special_accommodations = db.Column(db.JSON, nullable=True)  # Array of accommodations needed
    
    # Voting preferences and settings
    preferred_language = db.Column(db.String(10), default='en')
    accessibility_needs = db.Column(db.JSON, nullable=True)  # Array of accessibility requirements
    notification_preferences = db.Column(db.JSON, nullable=True)  # Communication preferences
    
    # Registration source and method
    registration_source = db.Column(db.String(50), nullable=True)  # mobile_app, web_portal, admin_import, third_party
    registration_method = db.Column(db.String(50), nullable=True)  # self_registration, admin_registration, bulk_import
    
    # Device and session information
    device_id = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    location_data = db.Column(db.JSON, nullable=True)
    
    # Document and verification tracking
    documents_submitted = db.Column(db.JSON, nullable=True)  # Array of document types submitted
    verification_documents = db.Column(db.JSON, nullable=True)  # Array of verification document info
    
    # Voting history and eligibility
    is_first_time_voter = db.Column(db.Boolean, default=True)
    previous_registrations = db.Column(db.JSON, nullable=True)  # Array of previous registration IDs
    voter_history_verified = db.Column(db.Boolean, default=False)
    
    # Compliance and audit
    compliance_checks = db.Column(db.JSON, nullable=True)  # Array of compliance check results
    audit_trail = db.Column(db.JSON, nullable=True)  # Array of audit events
    fraud_check_score = db.Column(db.Float, nullable=True)  # Fraud detection score
    risk_assessment = db.Column(db.String(20), nullable=True)  # low, medium, high, critical
    
    # Notification and communication
    notifications_sent = db.Column(db.JSON, nullable=True)  # Array of notifications sent
    confirmation_sent = db.Column(db.Boolean, default=False)
    reminder_sent = db.Column(db.Boolean, default=False)
    
    # Error handling
    error_count = db.Column(db.Integer, default=0)
    error_messages = db.Column(db.JSON, nullable=True)
    last_error = db.Column(db.String(500), nullable=True)
    
    # Relationships
    voter = db.relationship('Voter', backref='registrations')
    election = db.relationship('Election', backref='registrations')
    company = db.relationship('Company', backref='voter_registrations')
    processor = db.relationship('User', backref='processed_registrations')
    
    # Constraints and indexes
    __table_args__ = (
        db.UniqueConstraint('voter_id', 'election_id', name='unique_registration_per_election'),
        db.Index('idx_registration_status', 'status', 'registration_type'),
        db.Index('idx_registration_election', 'election_id', 'status'),
        db.Index('idx_registration_voter', 'voter_id', 'registered_at'),
        db.Index('idx_registration_verification', 'verification_level_met', 'eligibility_verified'),
        db.Index('idx_registration_geography', 'jurisdiction', 'precinct'),
    )
    
    def __repr__(self):
        return f'<VoterRegistration {self.registration_id} - {self.status}>'
    
    @property
    def is_approved(self):
        """Check if registration is approved"""
        return self.status == 'approved'
    
    @property
    def is_pending(self):
        """Check if registration is still pending"""
        return self.status == 'pending'
    
    @property
    def is_expired(self):
        """Check if registration has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_eligible_to_vote(self):
        """Check if voter is eligible to vote based on registration"""
        return (self.is_approved and 
                self.eligibility_verified and 
                not self.is_expired and
                self.verification_level_met in ['standard', 'full'])
    
    @property
    def verification_completion_percentage(self):
        """Get percentage of verification requirements completed"""
        total_checks = 4  # eligibility, identity, address, age
        completed_checks = sum([
            self.eligibility_verified,
            self.identity_verified,
            self.address_verified,
            self.age_verified
        ])
        return (completed_checks / total_checks) * 100
    
    def generate_registration_id(self):
        """Generate unique registration ID"""
        import secrets
        import string
        alphabet = string.ascii_uppercase + string.digits
        self.registration_id = f"REG-{''.join(secrets.choice(alphabet) for _ in range(12))}"
        return self.registration_id
    
    def add_audit_event(self, event_type, description, additional_data=None):
        """Add an event to the audit trail"""
        if not self.audit_trail:
            self.audit_trail = []
        
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'description': description,
            'additional_data': additional_data or {}
        }
        self.audit_trail.append(event)
    
    def approve_registration(self, approved_by_user_id, notes=None):
        """Approve the voter registration"""
        self.status = 'approved'
        self.approved_at = datetime.now(timezone.utc)
        self.processed_by = approved_by_user_id
        if notes:
            self.approval_notes = notes
        self.add_audit_event('approved', 'Registration approved')
    
    def reject_registration(self, rejected_by_user_id, reason):
        """Reject the voter registration"""
        self.status = 'rejected'
        self.rejected_at = datetime.now(timezone.utc)
        self.processed_by = rejected_by_user_id
        self.rejection_reason = reason
        self.add_audit_event('rejected', f'Registration rejected: {reason}')
    
    def update_verification_level(self):
        """Update verification level based on completed checks"""
        if self.eligibility_verified and self.identity_verified and self.address_verified and self.age_verified:
            self.verification_level_met = 'full'
        elif self.eligibility_verified and self.identity_verified:
            self.verification_level_met = 'standard'
        elif self.eligibility_verified:
            self.verification_level_met = 'basic'
        else:
            self.verification_level_met = 'none'
    
    def get_missing_requirements(self):
        """Get list of missing verification requirements"""
        missing = []
        if not self.eligibility_verified:
            missing.append('eligibility_verification')
        if not self.identity_verified:
            missing.append('identity_verification')
        if not self.address_verified:
            missing.append('address_verification')
        if not self.age_verified:
            missing.append('age_verification')
        return missing
    
    def get_registration_summary(self):
        """Get a summary of registration details"""
        return {
            'id': self.registration_id,
            'status': self.status,
            'type': self.registration_type,
            'registered_at': self.registered_at.isoformat(),
            'verification_level': self.verification_level_met,
            'verification_percentage': self.verification_completion_percentage,
            'is_eligible': self.is_eligible_to_vote,
            'missing_requirements': self.get_missing_requirements()
        } 
from app import db
from app.models.base import TimestampAuditMixin
from datetime import datetime, timezone
import hashlib
import json

class Vote(db.Model, TimestampAuditMixin):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    ballot_id = db.Column(db.Integer, db.ForeignKey('ballots.id'), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey('voters.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Vote identification and tracking
    vote_id = db.Column(db.String(100), unique=True, nullable=False)  # Unique vote identifier
    tracking_code = db.Column(db.String(50), unique=True, nullable=False)  # For voter tracking
    
    # Vote data (encrypted and structured)
    vote_data = db.Column(db.JSON, nullable=False)  # {"selections": [candidate_ids], "rankings": [], "write_ins": []}
    encrypted_vote_data = db.Column(db.Text, nullable=True)  # Encrypted version of vote data
    
    # Vote metadata
    vote_method = db.Column(db.String(50), default='mobile')  # mobile, web, kiosk, paper
    vote_type = db.Column(db.String(50), default='regular')  # regular, early, absentee, provisional
    is_test_vote = db.Column(db.Boolean, default=False)
    
    # Verification and security
    vote_hash = db.Column(db.String(255), nullable=False)  # Hash of vote data for integrity
    verification_hash = db.Column(db.String(255), nullable=False)  # Additional verification hash
    signature_hash = db.Column(db.String(255), nullable=True)  # Digital signature of vote
    
    # Authentication verification
    biometric_verified = db.Column(db.Boolean, default=False)
    device_verified = db.Column(db.Boolean, default=False)
    identity_verified = db.Column(db.Boolean, default=False)
    two_factor_verified = db.Column(db.Boolean, default=False)
    
    # Device and session information
    device_id = db.Column(db.String(255), nullable=True)
    device_fingerprint = db.Column(db.Text, nullable=True)  # JSON of device characteristics
    app_version = db.Column(db.String(50), nullable=True)
    operating_system = db.Column(db.String(100), nullable=True)
    
    # Network and location data
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6
    user_agent = db.Column(db.String(500), nullable=True)
    location_data = db.Column(db.JSON, nullable=True)  # GPS coordinates, city, country
    timezone = db.Column(db.String(50), nullable=True)
    
    # Timing information
    vote_start_time = db.Column(db.DateTime, nullable=True)  # When voter started voting
    vote_cast_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))  # When vote was submitted
    vote_processing_time = db.Column(db.DateTime, nullable=True)  # When vote was processed
    
    # Vote status and processing
    vote_status = db.Column(db.String(50), default='cast')  # cast, verified, counted, rejected, flagged
    processing_status = db.Column(db.String(50), default='pending')  # pending, processed, failed, auditing
    is_counted = db.Column(db.Boolean, default=False)
    is_auditable = db.Column(db.Boolean, default=True)
    
    # Paper trail and receipts
    receipt_generated = db.Column(db.Boolean, default=False)
    receipt_code = db.Column(db.String(100), nullable=True)
    paper_ballot_id = db.Column(db.String(100), nullable=True)  # If printed to paper
    
    # Audit and compliance
    audit_trail = db.Column(db.JSON, nullable=True)  # Array of audit events
    compliance_verified = db.Column(db.Boolean, default=False)
    chain_of_custody = db.Column(db.JSON, nullable=True)  # Tracking through system
    
    # Blockchain integration (for future use)
    blockchain_tx_id = db.Column(db.String(255), nullable=True)
    blockchain_block_number = db.Column(db.Integer, nullable=True)
    blockchain_confirmed = db.Column(db.Boolean, default=False)
    
    # Error handling and issues
    error_count = db.Column(db.Integer, default=0)
    error_messages = db.Column(db.JSON, nullable=True)  # Array of error messages
    warning_flags = db.Column(db.JSON, nullable=True)  # Array of warning flags
    
    # Relationships
    election = db.relationship('Election', backref='votes')
    ballot = db.relationship('Ballot', backref='votes')
    voter = db.relationship('Voter', backref='votes')
    company = db.relationship('Company', backref='votes')
    
    # Constraints and indexes
    __table_args__ = (
        db.UniqueConstraint('voter_id', 'ballot_id', name='unique_vote_per_ballot'),
        db.Index('idx_vote_election', 'election_id', 'vote_status'),
        db.Index('idx_vote_ballot', 'ballot_id', 'is_counted'),
        db.Index('idx_vote_tracking', 'tracking_code'),
        db.Index('idx_vote_timestamp', 'vote_cast_time'),
        db.Index('idx_vote_verification', 'verification_hash'),
        db.Index('idx_vote_status', 'vote_status', 'processing_status'),
    )
    
    def __repr__(self):
        return f'<Vote {self.vote_id} - {self.ballot.title if self.ballot else "Unknown Ballot"}>'
    
    @property
    def is_verified(self):
        """Check if vote has been fully verified"""
        return (self.biometric_verified and 
                self.device_verified and 
                self.identity_verified and 
                self.vote_status in ['verified', 'counted'])
    
    @property
    def verification_level(self):
        """Get the verification level of this vote"""
        levels = []
        if self.identity_verified:
            levels.append('identity')
        if self.biometric_verified:
            levels.append('biometric')
        if self.device_verified:
            levels.append('device')
        if self.two_factor_verified:
            levels.append('2fa')
        return ','.join(levels) if levels else 'none'
    
    def generate_tracking_code(self):
        """Generate a unique tracking code for this vote"""
        import secrets
        import string
        alphabet = string.ascii_uppercase + string.digits
        self.tracking_code = ''.join(secrets.choice(alphabet) for _ in range(12))
        return self.tracking_code
    
    def _format_cast_time(self):
        """Format vote_cast_time consistently regardless of tzinfo presence (naive vs aware UTC)"""
        if not self.vote_cast_time:
            return ""
        if isinstance(self.vote_cast_time, datetime):
            return self.vote_cast_time.replace(tzinfo=None).isoformat()
        return str(self.vote_cast_time)

    def generate_vote_hash(self):
        """Generate integrity hash for vote data"""
        vote_string = json.dumps(self.vote_data, sort_keys=True)
        cast_time_str = self._format_cast_time()
        hash_input = f"{self.voter_id}{self.ballot_id}{vote_string}{cast_time_str}"
        self.vote_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        return self.vote_hash
    
    def generate_verification_hash(self):
        """Generate verification hash for audit purposes"""
        verification_string = f"{self.vote_hash}{self.voter_id}{self.device_id or ''}"
        self.verification_hash = hashlib.sha256(verification_string.encode()).hexdigest()
        return self.verification_hash

    def compute_vote_hash(self):
        """Recompute expected vote hash from current fields without mutating self.vote_hash"""
        vote_string = json.dumps(self.vote_data, sort_keys=True) if self.vote_data is not None else ""
        cast_time_str = self._format_cast_time()
        hash_input = f"{self.voter_id}{self.ballot_id}{vote_string}{cast_time_str}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def compute_verification_hash(self, current_vote_hash=None):
        """Recompute expected verification hash without mutating self.verification_hash"""
        v_hash = current_vote_hash or self.vote_hash or ""
        verification_string = f"{v_hash}{self.voter_id}{self.device_id or ''}"
        return hashlib.sha256(verification_string.encode()).hexdigest()

    def verify_integrity(self):
        """
        Verify vote integrity by recomputing hashes from current stored fields and comparing to stored hashes.

        NOTE ON SECURITY SCOPE & LIMITATIONS:
        This hash verification can catch accidental data corruption or an unintended application bug
        that mutates a vote row after casting, but it cannot catch deliberate tampering by anyone with DB write access,
        since they could recompute a matching hash.
        """
        expected_vote_hash = self.compute_vote_hash()
        vote_hash_valid = (self.vote_hash == expected_vote_hash)

        expected_ver_hash = self.compute_verification_hash(expected_vote_hash)
        ver_hash_valid = (self.verification_hash == expected_ver_hash)

        is_valid = vote_hash_valid and ver_hash_valid
        return {
            'is_valid': is_valid,
            'integrity_verified': is_valid,
            'vote_hash_match': vote_hash_valid,
            'verification_hash_match': ver_hash_valid,
            'stored_vote_hash': self.vote_hash,
            'computed_vote_hash': expected_vote_hash,
            'stored_verification_hash': self.verification_hash,
            'computed_verification_hash': expected_ver_hash
        }
    
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
    
    def get_selected_candidates(self):
        """Get list of selected candidate IDs"""
        if not self.vote_data:
            return []
        data = self.vote_data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return []
        if isinstance(data, dict):
            if 'candidate_selections' in data:
                return data['candidate_selections']
            elif 'selections' in data:
                return data['selections']
            elif 'selected_candidates' in data:
                return data['selected_candidates']
        return []
    
    def get_write_in_candidates(self):
        """Get list of write-in candidate names"""
        if not self.vote_data:
            return []
        data = self.vote_data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return []
        if isinstance(data, dict):
            if 'write_in_candidates' in data:
                return data['write_in_candidates']
            elif 'write_ins' in data:
                return data['write_ins']
        return []
    
    def validate_vote_data(self):
        """Validate vote data against ballot rules"""
        if not self.ballot:
            return False, "Ballot not found"
        
        selections = self.get_selected_candidates()
        selection_count = len(selections)
        
        # Check minimum selections
        if selection_count < self.ballot.min_selections:
            return False, f"Must select at least {self.ballot.min_selections} candidates"
        
        # Check maximum selections
        if selection_count > self.ballot.max_selections:
            return False, f"Cannot select more than {self.ballot.max_selections} candidates"
        
        # Validate candidate IDs exist
        from app.models.candidate import Candidate
        from app.utils.constants import STATUS_ACTIVE
        valid_candidate_ids = [c.id for c in self.ballot.candidates if c.is_active and c.status == STATUS_ACTIVE]
        
        for candidate_id in selections:
            if candidate_id not in valid_candidate_ids:
                return False, f"Invalid candidate ID: {candidate_id}"
        
        return True, "Vote data is valid" 
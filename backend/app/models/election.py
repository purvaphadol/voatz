from app import db
from app.models.base import TimestampAuditMixin
from datetime import datetime, timezone

class Election(db.Model, TimestampAuditMixin):
    __tablename__ = 'elections'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Election basic information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    election_code = db.Column(db.String(50), nullable=False)  # Scoped unique per company
    
    # Election classification
    election_type = db.Column(db.String(50), nullable=False)  # municipal, state, federal, corporate, university, poll
    election_category = db.Column(db.String(50), nullable=True)  # primary, general, special, referendum
    
    # Timing and scheduling
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    registration_deadline = db.Column(db.DateTime, nullable=True)
    early_voting_start = db.Column(db.DateTime, nullable=True)
    early_voting_end = db.Column(db.DateTime, nullable=True)
    
    # Election settings and rules
    allow_early_voting = db.Column(db.Boolean, default=False)
    require_biometric = db.Column(db.Boolean, default=True)
    require_photo_id = db.Column(db.Boolean, default=True)
    allow_overseas_voting = db.Column(db.Boolean, default=False)
    allow_military_voting = db.Column(db.Boolean, default=False)
    
    # Voting configuration
    max_votes_per_voter = db.Column(db.Integer, default=1)
    allow_vote_changes = db.Column(db.Boolean, default=False)  # Can voters change their vote before election ends
    require_all_ballots = db.Column(db.Boolean, default=False)  # Must vote on all ballots
    
    # Geographic and jurisdictional
    jurisdiction = db.Column(db.String(100), nullable=True)
    geographic_scope = db.Column(db.String(100), nullable=True)  # city, county, state, federal, corporate
    eligible_voter_types = db.Column(db.String(200), default='standard')  # comma-separated: standard,overseas,military
    
    # Election status and lifecycle
    # NOTE: Election.status is a business-workflow status ('draft', 'published', 'active', 'voting', 'completed', 'cancelled', 'auditing'), distinct from the integer governance status (1=Active, 0=Inactive, 9=Deactivated) used elsewhere in this codebase. 'cancelled' is treated as deactivated for governance filtering.
    status = db.Column(db.String(20), default='draft')  # draft, published, active, voting, completed, cancelled, auditing
    is_public = db.Column(db.Boolean, default=True)  # Is this election publicly visible
    is_test_election = db.Column(db.Boolean, default=False)  # Is this a test/demo election
    
    # Results and reporting
    results_published = db.Column(db.Boolean, default=False)
    results_published_at = db.Column(db.DateTime, nullable=True)
    total_registered_voters = db.Column(db.Integer, default=0)
    total_votes_cast = db.Column(db.Integer, default=0)
    turnout_percentage = db.Column(db.Float, default=0.0)
    
    # Security and audit
    election_hash = db.Column(db.String(255), nullable=True)  # Hash of election configuration
    audit_enabled = db.Column(db.Boolean, default=True)
    paper_trail_required = db.Column(db.Boolean, default=True)
    
    # Relationships
    company = db.relationship('Company', backref='elections')
    
    # Constraints and indexes
    __table_args__ = (
        db.UniqueConstraint('company_id', 'election_code', name='unique_election_code_per_company'),
        db.Index('idx_election_company_status', 'company_id', 'status'),
        db.Index('idx_election_dates', 'start_date', 'end_date'),
        db.Index('idx_election_status', 'status', 'is_public'),
        db.Index('idx_election_type', 'election_type', 'election_category'),
    )
    
    def __repr__(self):
        return f'<Election {self.title} ({self.election_code})>'
    
    @property
    def is_active(self):
        """Check if election is currently active for voting"""
        now = datetime.now(timezone.utc)
        start = self.start_date.replace(tzinfo=timezone.utc) if self.start_date and self.start_date.tzinfo is None else self.start_date
        end = self.end_date.replace(tzinfo=timezone.utc) if self.end_date and self.end_date.tzinfo is None else self.end_date
        return (self.status == 'active' and start <= now <= end)
    
    @property
    def is_early_voting_active(self):
        """Check if early voting is currently active"""
        if not self.allow_early_voting or not self.early_voting_start or not self.early_voting_end:
            return False
        now = datetime.now(timezone.utc)
        ev_start = self.early_voting_start.replace(tzinfo=timezone.utc) if self.early_voting_start.tzinfo is None else self.early_voting_start
        ev_end = self.early_voting_end.replace(tzinfo=timezone.utc) if self.early_voting_end.tzinfo is None else self.early_voting_end
        return (self.status == 'active' and ev_start <= now <= ev_end)
    
    @property
    def voting_window_status(self):
        """Get current voting window status"""
        now = datetime.now(timezone.utc)
        start = self.start_date.replace(tzinfo=timezone.utc) if self.start_date and self.start_date.tzinfo is None else self.start_date
        end = self.end_date.replace(tzinfo=timezone.utc) if self.end_date and self.end_date.tzinfo is None else self.end_date
        if now < start:
            return 'upcoming'
        elif now > end:
            return 'ended'
        elif self.is_early_voting_active:
            return 'early_voting'
        elif self.is_active:
            return 'voting'
        else:
            return 'inactive' 
from app import db
from app.models.base import TimestampAuditMixin

class Ballot(db.Model, TimestampAuditMixin):
    __tablename__ = 'ballots'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Ballot identification
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ballot_code = db.Column(db.String(50), nullable=False)  # Unique within election
    
    # Ballot configuration
    ballot_type = db.Column(db.String(50), nullable=False)  # single_choice, multiple_choice, ranked_choice, approval, write_in
    position_title = db.Column(db.String(100), nullable=True)  # Mayor, Governor, President, etc.
    
    # Voting rules
    min_selections = db.Column(db.Integer, default=0)  # Minimum selections required
    max_selections = db.Column(db.Integer, default=1)  # Maximum selections allowed
    allow_write_in = db.Column(db.Boolean, default=False)
    require_selection = db.Column(db.Boolean, default=True)  # Is this ballot mandatory
    
    # Display and ordering
    order_index = db.Column(db.Integer, default=0)  # Order of ballot in election
    display_format = db.Column(db.String(50), default='list')  # list, grid, carousel
    randomize_candidates = db.Column(db.Boolean, default=False)  # Randomize candidate order per voter
    
    # Ballot content
    instructions = db.Column(db.Text, nullable=True)  # Voting instructions for this ballot
    question_text = db.Column(db.Text, nullable=True)  # For referendum/proposition ballots
    
    # Geographic and eligibility restrictions
    jurisdiction_restriction = db.Column(db.String(100), nullable=True)  # Limit to specific area
    voter_type_restriction = db.Column(db.String(200), nullable=True)  # Limit to voter types
    
    # Status and configuration
    is_active = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=False)
    is_test_ballot = db.Column(db.Boolean, default=False)
    
    # Results tracking
    total_votes_cast = db.Column(db.Integer, default=0)
    total_eligible_voters = db.Column(db.Integer, default=0)
    
    # Security
    ballot_hash = db.Column(db.String(255), nullable=True)  # Hash of ballot configuration
    
    # Relationships
    election = db.relationship('Election', backref='ballots')
    company = db.relationship('Company', backref='ballots')
    
    # Constraints and indexes
    __table_args__ = (
        db.UniqueConstraint('ballot_code', 'election_id', name='unique_ballot_per_election'),
        db.Index('idx_ballot_election', 'election_id', 'is_active'),
        db.Index('idx_ballot_order', 'election_id', 'order_index'),
        db.Index('idx_ballot_type', 'ballot_type', 'is_published'),
    )
    
    def __repr__(self):
        return f'<Ballot {self.title} - {self.election.title if self.election else "Unknown Election"}>'
    
    @property
    def is_single_choice(self):
        """Check if this is a single choice ballot"""
        return self.ballot_type == 'single_choice' and self.max_selections == 1
    
    @property
    def is_multiple_choice(self):
        """Check if this allows multiple selections"""
        return self.ballot_type == 'multiple_choice' and self.max_selections > 1
    
    @property
    def is_ranked_choice(self):
        """Check if this is ranked choice voting"""
        return self.ballot_type == 'ranked_choice'
    
    @property
    def is_referendum(self):
        """Check if this is a yes/no referendum ballot"""
        return self.ballot_type in ['referendum', 'proposition', 'yes_no']
    
    def get_selection_rules_text(self):
        """Get human-readable selection rules"""
        if self.is_single_choice:
            return f"Select 1 candidate"
        elif self.min_selections == self.max_selections:
            return f"Select exactly {self.max_selections} candidates"
        elif self.min_selections == 0:
            return f"Select up to {self.max_selections} candidates"
        else:
            return f"Select {self.min_selections} to {self.max_selections} candidates" 
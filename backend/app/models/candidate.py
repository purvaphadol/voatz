from app import db
from app.models.base import TimestampAuditMixin

class Candidate(db.Model, TimestampAuditMixin):
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    ballot_id = db.Column(db.Integer, db.ForeignKey('ballots.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Candidate identification
    name = db.Column(db.String(200), nullable=False)
    candidate_code = db.Column(db.String(50), nullable=False)  # Unique within ballot
    
    # Candidate information
    party = db.Column(db.String(100), nullable=True)
    party_abbreviation = db.Column(db.String(10), nullable=True)
    title = db.Column(db.String(100), nullable=True)  # Current title/position
    
    # Candidate details
    description = db.Column(db.Text, nullable=True)
    biography = db.Column(db.Text, nullable=True)
    platform_summary = db.Column(db.Text, nullable=True)
    
    # Media and presentation
    image_url = db.Column(db.Text, nullable=True)  # Changed to TEXT for base64 images
    profile_image_path = db.Column(db.String(500), nullable=True)
    campaign_website = db.Column(db.String(200), nullable=True)
    social_media_links = db.Column(db.JSON, nullable=True)  # JSON object with social links
    
    # Display and ordering
    order_index = db.Column(db.Integer, default=0)  # Order on ballot
    display_name = db.Column(db.String(200), nullable=True)  # Alternative display name
    
    # Special candidate types
    is_write_in = db.Column(db.Boolean, default=False)  # Is this a write-in placeholder
    is_incumbent = db.Column(db.Boolean, default=False)
    is_endorsed = db.Column(db.Boolean, default=False)
    
    # Contact and background
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    # Eligibility and verification
    age = db.Column(db.Integer, nullable=True)
    years_in_office = db.Column(db.Integer, nullable=True)
    education = db.Column(db.String(200), nullable=True)
    occupation = db.Column(db.String(100), nullable=True)
    
    # Campaign information
    campaign_finance_id = db.Column(db.String(50), nullable=True)
    endorsements = db.Column(db.Text, nullable=True)  # List of endorsements
    key_issues = db.Column(db.JSON, nullable=True)  # Array of key campaign issues
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_qualified = db.Column(db.Boolean, default=True)
    is_withdrawn = db.Column(db.Boolean, default=False)
    withdrawal_date = db.Column(db.DateTime, nullable=True)
    withdrawal_reason = db.Column(db.String(200), nullable=True)
    
    # Results tracking
    total_votes_received = db.Column(db.Integer, default=0)
    vote_percentage = db.Column(db.Float, default=0.0)
    rank_position = db.Column(db.Integer, nullable=True)  # Final ranking in results
    
    # Relationships
    ballot = db.relationship('Ballot', backref='candidates')
    company = db.relationship('Company', backref='candidates')
    
    # Constraints and indexes
    __table_args__ = (
        db.UniqueConstraint('candidate_code', 'ballot_id', name='unique_candidate_per_ballot'),
        db.Index('idx_candidate_ballot', 'ballot_id', 'is_active'),
        db.Index('idx_candidate_order', 'ballot_id', 'order_index'),
        db.Index('idx_candidate_party', 'party', 'is_active'),
        db.Index('idx_candidate_name', 'name'),
    )
    
    def __repr__(self):
        return f'<Candidate {self.name} ({self.party or "Independent"})>'
    
    @property
    def full_display_name(self):
        """Get the full display name with party if available"""
        base_name = self.display_name or self.name
        if self.party_abbreviation:
            return f"{base_name} ({self.party_abbreviation})"
        elif self.party:
            return f"{base_name} ({self.party})"
        return base_name
    
    @property
    def party_display(self):
        """Get party for display purposes"""
        if self.party_abbreviation:
            return self.party_abbreviation
        elif self.party:
            return self.party
        return "Independent"
    
    @property
    def is_special_option(self):
        """Check if this is a special ballot option (write-in, none of above, etc.)"""
        special_names = ['write-in', 'none of the above', 'abstain', 'no preference']
        return self.name.lower() in special_names or self.is_write_in
    
    def get_vote_summary(self):
        """Get formatted vote summary"""
        if self.total_votes_received == 0:
            return "No votes"
        elif self.total_votes_received == 1:
            return "1 vote"
        else:
            percentage_text = f" ({self.vote_percentage:.1f}%)" if self.vote_percentage > 0 else ""
            return f"{self.total_votes_received:,} votes{percentage_text}" 
from app import db
from app.models.base import TimestampAuditMixin

class Module(db.Model, TimestampAuditMixin):
    __tablename__ = 'modules'
    id = db.Column(db.Integer, primary_key=True)
    module_name = db.Column(db.String(100), nullable=False)
    route_name = db.Column(db.String(100), nullable=True)  # Custom route name (e.g., 'testing')
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), nullable=True)
    order_index = db.Column(db.Integer, default=0, nullable=False)  # Order for sidebar display
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Relationships
    company = db.relationship('Company', backref='modules')
    
    @property
    def display_route(self):
        """Return the route to use - either custom route_name or lowercase module_name"""
        return self.route_name if self.route_name else self.module_name.lower().replace(' ', '')

    @property
    def is_active(self):
        """Backward compatibility — True if status is active (1)"""
        return self.status == 1
    
    __table_args__ = (
        db.UniqueConstraint('module_name', 'company_id', name='unique_module_per_company'),
        db.UniqueConstraint('route_name', 'company_id', name='unique_route_per_company'),
    )

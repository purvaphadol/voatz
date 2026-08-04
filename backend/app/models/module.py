from app import db
from app.models.base import TimestampAuditMixin

class SystemModule(db.Model, TimestampAuditMixin):
    """Global Master Module Catalog managed exclusively by Platform Administrator."""
    __tablename__ = 'system_modules'

    id = db.Column(db.Integer, primary_key=True)
    module_name = db.Column(db.String(100), unique=True, nullable=False)
    route_name = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), default='folder', nullable=True)
    order_index = db.Column(db.Integer, default=0, nullable=False)

    @property
    def display_route(self):
        """Return route to use — either custom route_name or lowercase module_name without spaces."""
        return self.route_name if self.route_name else self.module_name.lower().replace(' ', '')

    @property
    def is_active(self):
        return self.status == 1


class SystemModuleAction(db.Model, TimestampAuditMixin):
    """Global Master Module Actions associated with a SystemModule."""
    __tablename__ = 'system_module_actions'

    id = db.Column(db.Integer, primary_key=True)
    action_name = db.Column(db.String(100), nullable=False)
    action_url = db.Column(db.String(255), nullable=False)
    system_module_id = db.Column(db.Integer, db.ForeignKey('system_modules.id', ondelete='CASCADE'), nullable=False)

    system_module = db.relationship('SystemModule', backref=db.backref('actions', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('system_module_id', 'action_name', name='uq_system_module_action'),
    )


class CompanyModule(db.Model, TimestampAuditMixin):
    """Mapping table for provisioning SystemModules to specific Companies (Tenants)."""
    __tablename__ = 'company_modules'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    system_module_id = db.Column(db.Integer, db.ForeignKey('system_modules.id', ondelete='CASCADE'), nullable=False)

    company = db.relationship('Company', backref=db.backref('company_modules', cascade='all, delete-orphan'))
    system_module = db.relationship('SystemModule', backref=db.backref('company_allocations', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('company_id', 'system_module_id', name='uq_company_system_module'),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

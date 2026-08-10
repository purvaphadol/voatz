from app import db
from app.models.base import TimestampAuditMixin, TenantScopedMixin, StatusEnum

class UserRoleMapping(db.Model, TimestampAuditMixin, TenantScopedMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    status = db.Column(db.Integer, default=StatusEnum.ACTIVE, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', 'department_id', 'company_id', name='uq_user_role_dept_company'),
    )


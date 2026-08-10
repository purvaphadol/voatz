from datetime import datetime, timezone
from enum import IntEnum
from sqlalchemy import Column, Integer, DateTime, event
from sqlalchemy.orm import Session, with_loader_criteria
from flask_sqlalchemy.query import Query

def _now():
    return datetime.now(timezone.utc)

class StatusEnum(IntEnum):
    INACTIVE = 0
    ACTIVE = 1
    DELETED = 9

class ActiveQuery(Query):
    """Custom Query class for models with status fields.
    Automatically excludes status=9 (deactivated) records unless .with_deactivated() is called.
    """
    def with_deactivated(self):
        """Include deactivated (status=9) records in query results."""
        return self.execution_options(include_deactivated=True)


class TimestampAuditMixin:
    """Mixin that adds created_at, updated_at, created_by, updated_by, status
    to any SQLAlchemy model. Uses no db instance — columns are declared with
    plain sqlalchemy types so they bind to whatever db the model uses."""

    created_at  = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at  = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
    created_by  = Column(Integer, nullable=True)
    updated_by  = Column(Integer, nullable=True)
    status      = Column(Integer, default=StatusEnum.ACTIVE, nullable=False)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TenantScopedMixin:
    """Base mixin for all tenant-aware database models providing standardized tenant scoping and status lifecycle management."""

    @classmethod
    def query_tenant(cls, current_user, include_inactive=False):
        """Standardized query builder for tenant isolation & status scoping."""
        query = cls.query

        # 1. Tenant Scoping: Platform Admin accesses all; others restricted to user's company_id
        is_platform_admin = getattr(current_user, 'is_administrator', False) or getattr(current_user, 'is_platform_admin', False)
        if not is_platform_admin and hasattr(cls, 'company_id'):
            user_company_id = getattr(current_user, 'company_id', None)
            query = query.filter(cls.company_id == user_company_id)

        # 2. Status Filtering
        if hasattr(cls, 'status'):
            if not include_inactive:
                query = query.filter(cls.status == StatusEnum.ACTIVE)
            else:
                query = query.filter(cls.status != StatusEnum.DELETED)

        return query

    def soft_delete(self):
        """Standardized soft deletion."""
        if hasattr(self, 'status'):
            self.status = StatusEnum.DELETED

    def toggle_active(self):
        """Standardized active status toggle between ACTIVE (1) and INACTIVE (0)."""
        if hasattr(self, 'status'):
            self.status = StatusEnum.INACTIVE if self.status == StatusEnum.ACTIVE else StatusEnum.ACTIVE


@event.listens_for(Session, "do_orm_execute")
def _auto_filter_deactivated(execute_state):
    """Global ORM event listener:
    Automatically filters out status == 9 (deactivated) records for all SELECT queries
    targeting models with integer status columns, unless include_deactivated=True is explicitly set.
    """
    if (
        execute_state.is_select
        and not execute_state.execution_options.get("include_deactivated", False)
    ):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                TimestampAuditMixin,
                lambda cls: cls.status != StatusEnum.DELETED if (hasattr(cls, 'status') and isinstance(cls.status.type, Integer)) else True,
                include_aliases=True
            )
        )
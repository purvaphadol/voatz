from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, event
from sqlalchemy.orm import Session, with_loader_criteria
from flask_sqlalchemy.query import Query

def _now():
    return datetime.now(timezone.utc)

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
    status      = Column(Integer, default=1, nullable=False)


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
                lambda cls: cls.status != 9 if (hasattr(cls, 'status') and isinstance(cls.status.type, Integer)) else True,
                include_aliases=True
            )
        )
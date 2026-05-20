from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, DateTime


def _now():
    return datetime.now(timezone.utc)

class TimestampAuditMixin:
    """Mixin that adds created_at, updated_at, created_by, updated_by, status
    to any SQLAlchemy model. Uses no db instance — columns are declared with
    plain sqlalchemy types so they bind to whatever db the model uses."""

    created_at  = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at  = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
    created_by  = Column(Integer, nullable=True)
    updated_by  = Column(Integer, nullable=True)
    status      = Column(Integer, default=1, nullable=False)
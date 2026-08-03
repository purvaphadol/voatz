# User and Entity Statuses
STATUS_ACTIVE = 1       # Active: Operational, enabled, open for use
STATUS_INACTIVE = 0     # Inactive: Paused / disabled, but can be reactivated later
STATUS_DEACTIVATED = 9  # Soft-Deleted / Historical: Excluded from all UI & standard queries

# Pagination Defaults
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 1000

# Security Defaults
MIN_PASSWORD_LENGTH = 8

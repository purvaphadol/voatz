# User and Entity Statuses
STATUS_ACTIVE = 1       # Active: Operational, enabled, open for use
STATUS_INACTIVE = 0     # Inactive / Soft-Deleted: Disabled/archived
STATUS_DEACTIVATED = 9  # Permanently Soft-Deleted / Historical: Excluded from all UI & standard queries

# Pagination Defaults
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 1000

# Security Defaults
MIN_PASSWORD_LENGTH = 8

# Platform Admin Only Messages
MSG_PLATFORM_ADMIN_ONLY_MODULE_CREATE = (
    'Adding a new module requires software route configuration. '
    'To add a custom module to your subscription plan, please '
    'contact your Platform Administrator.'
)
MSG_PLATFORM_ADMIN_ONLY_MODULE_UPDATE = (
    'Modifying a module requires Platform Administrator access. '
    'Please contact your Platform Administrator to make this change.'
)
MSG_PLATFORM_ADMIN_ONLY_MODULE_DELETE = (
    'Adding / deleting a new module requires software route configuration. '
    'To add a custom module to your company subscription plan, please '
    'contact your Platform Administrator at admin@voatz.com.'
)
MSG_PLATFORM_ADMIN_ONLY_MODULE_ACTIONS = (
    'Modifying module actions requires Platform Administrator access. '
    'Please contact your Platform Administrator to make this change.'
)


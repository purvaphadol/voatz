from flask import jsonify

class ApiResponse:
    """Standardized API Response wrapper to ensure consistent JSON structures across all endpoints."""

    @staticmethod
    def success(data=None, message="Success", status_code=200, **extra_fields):
        """Return a standardized JSON success response wrapper."""
        payload = {
            "success": True,
            "message": message
        }
        if data is not None:
            payload["data"] = data
        if extra_fields:
            payload.update(extra_fields)
        return jsonify(payload), status_code

    @staticmethod
    def error(message="An error occurred", details=None, status_code=400, **extra_fields):
        """Return a standardized JSON error response wrapper."""
        payload = {
            "success": False,
            "error": message
        }
        if details is not None:
            payload["details"] = details
        if extra_fields:
            payload.update(extra_fields)
        return jsonify(payload), status_code

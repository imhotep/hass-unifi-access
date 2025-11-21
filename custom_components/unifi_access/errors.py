"""Compatibility shim for API errors."""

from unifi_access_api.errors import ApiAuthError, ApiError

__all__ = ["ApiAuthError", "ApiError"]

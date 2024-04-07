"""Unifi Access Errors.

This module lists Unifi Access API errors.
"""


class ApiAuthError(Exception):
    """Raised when we can't authenticate with the API Token."""


class ApiError(Exception):
    """Raised when we have some trouble using the API."""

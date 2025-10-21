"""Unifi Access User Module."""

from collections.abc import Callable
import logging
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)


class UnifiAccessUser:
    """Unifi Access User Class."""

    def __init__(
        self,
        user_id: str,
        username: str,
        full_name: str,
        email: str,
        status: str,
        pin_code: str | None,
        hub,
        **kwargs: Any,
    ) -> None:
        """Initialize user."""
        self._callbacks: set[Callable] = set()
        self._hub = hub
        self._id = user_id
        self.username = username
        self.full_name = full_name
        self.email = email
        self.status = status
        self.pin_code = pin_code
        
        # Store additional user data
        self.first_name = kwargs.get("first_name", "")
        self.last_name = kwargs.get("last_name", "")
        self.phone = kwargs.get("phone", "")
        self.employee_number = kwargs.get("employee_number", "")
        self.email_status = kwargs.get("email_status", "UNVERIFIED")
        self.alias = kwargs.get("alias", "")
        self.nfc_cards = kwargs.get("nfc_cards", [])
        self.touch_pass = kwargs.get("touch_pass")
        self.user_email = kwargs.get("user_email", "")
        self.avatar_relative_path = kwargs.get("avatar_relative_path", "")
        self.onboard_time = kwargs.get("onboard_time", 0)

    @property
    def id(self) -> str:
        """Get user ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get user display name."""
        return self.full_name or self.username

    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == "ACTIVE"

    @property
    def is_deactivated(self) -> bool:
        """Check if user is deactivated."""
        return self.status == "DEACTIVATED"

    @property
    def has_pin(self) -> bool:
        """Check if user has a PIN code set."""
        return self.pin_code is not None

    @property
    def has_nfc_cards(self) -> bool:
        """Check if user has NFC cards."""
        return len(self.nfc_cards) > 0

    @property
    def has_touch_pass(self) -> bool:
        """Check if user has touch pass (mobile access)."""
        return self.touch_pass is not None and self.touch_pass.get("status") == "ACTIVE"

    def enable(self) -> None:
        """Enable user."""
        if not self.is_active:
            _LOGGER.info("Enabling user %s (%s)", self.name, self.id)
            self._hub.update_user_status(self.id, "ACTIVE")
            self.status = "ACTIVE"
        else:
            _LOGGER.warning("User %s (%s) is already active", self.name, self.id)

    def disable(self) -> None:
        """Disable user."""
        if self.is_active:
            _LOGGER.info("Disabling user %s (%s)", self.name, self.id)
            self._hub.update_user_status(self.id, "DEACTIVATED")
            self.status = "DEACTIVATED"
        else:
            _LOGGER.warning("User %s (%s) is already deactivated", self.name, self.id)

    def set_pin_code(self, pin_code: str | None) -> None:
        """Set user PIN code."""
        _LOGGER.info("Setting PIN code for user %s (%s)", self.name, self.id)
        self._hub.update_user_pin(self.id, pin_code)
        self.pin_code = pin_code

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when user changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update user data from API response."""
        self.status = data.get("status", self.status)
        self.pin_code = data.get("pin_code", self.pin_code)
        self.email = data.get("email", self.email)
        self.first_name = data.get("first_name", self.first_name)
        self.last_name = data.get("last_name", self.last_name)
        self.full_name = data.get("full_name", self.full_name)
        self.phone = data.get("phone", self.phone)
        self.employee_number = data.get("employee_number", self.employee_number)
        self.email_status = data.get("email_status", self.email_status)
        self.alias = data.get("alias", self.alias)
        self.nfc_cards = data.get("nfc_cards", self.nfc_cards)
        self.touch_pass = data.get("touch_pass", self.touch_pass)
        self.user_email = data.get("user_email", self.user_email)
        self.avatar_relative_path = data.get("avatar_relative_path", self.avatar_relative_path)
        self.onboard_time = data.get("onboard_time", self.onboard_time)

    def __eq__(self, value) -> bool:
        """Check if two users are equal."""
        if isinstance(value, UnifiAccessUser):
            return (
                self.id == value.id
                and self.username == value.username
                and self.full_name == value.full_name
                and self.email == value.email
                and self.status == value.status
            )
        return False

    def __repr__(self):
        """Return string representation of user."""
        return f"<UnifiAccessUser id={self.id} name={self.name} username={self.username} status={self.status} email={self.email}>"
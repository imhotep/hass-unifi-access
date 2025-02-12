"""Unifi Access Door Module."""

from collections.abc import Callable
import logging

_LOGGER = logging.getLogger(__name__)


class UnifiAccessDoor:
    """Unifi Access Door Class."""

    def __init__(
        self,
        door_id: str,
        name: str,
        door_position_status: str,
        door_lock_relay_status: str,
        door_lock_rule: str,
        door_lock_rule_ended_time: int,
        hub,
    ) -> None:
        """Initialize door."""
        self._callbacks: set[Callable] = set()
        self._event_listeners: dict[str, set] = {
            "access": set(),
            "doorbell_press": set(),
        }
        self._is_locking = False
        self._is_unlocking = False
        self._hub = hub
        self.hub_type = "UAH"
        self._id = door_id
        self.name = name
        self.door_position_status = door_position_status
        self.door_lock_relay_status = door_lock_relay_status
        self.doorbell_request_id = None
        self.lock_rule = door_lock_rule
        self.lock_rule_interval = 10
        self.lock_rule_ended_time = door_lock_rule_ended_time
        self.thumbnail = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x05\x01\x02"
            b"\x0a\x15\xbd"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        self.thumbnail_last_updated = None

    @property
    def doorbell_pressed(self) -> bool:
        """Get doorbell pressed status."""
        return self.doorbell_request_id is not None

    @property
    def id(self) -> str:
        """Get door ID."""
        return self._id

    @property
    def is_open(self):
        """Get door status."""
        return self.door_position_status == "open"

    @property
    def is_locked(self):
        """Solely used for locked state when calling lock."""
        if self.door_lock_relay_status == "":
            self.door_lock_relay_status = "lock"
            _LOGGER.warning("Relay status not set - assuming locked")
        return self.door_lock_relay_status == "lock"

    @property
    def is_locking(self):
        """Solely used for locking state when calling lock."""
        return False

    @property
    def is_unlocking(self):
        """Solely used for unlocking state when calling unlock."""
        return self._is_unlocking

    def open(self) -> None:
        """Open door."""
        self.unlock()

    def unlock(self) -> None:
        """Unlock door."""
        if self.is_locked:
            self._is_unlocking = True
            self._hub.unlock_door(self._id)
            self._is_unlocking = False
            _LOGGER.info("Door with door ID %s is unlocked", self.id)
        else:
            _LOGGER.error("Door with door ID %s is already unlocked", self.id)

    def set_lock_rule(self, lock_rule_type) -> None:
        """Set lock rule."""
        new_door_lock_rule = {"type": lock_rule_type}
        if lock_rule_type == "custom":
            new_door_lock_rule["interval"] = self.lock_rule_interval
        self._hub.set_door_lock_rule(self._id, new_door_lock_rule)

    def get_lock_rule(self) -> None:
        """Get lock rule."""
        self._hub.get_door_lock_rule(self._id)

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when door changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()

    def add_event_listener(
        self, event: str, callback: Callable[[str, dict[str, str]], None]
    ) -> None:
        """Add event listener."""
        if self._event_listeners.get(event) is not None:
            self._event_listeners[event].add(callback)
            _LOGGER.info("Registered event %s for door %s", event, self.name)

    def remove_event_listener(
        self, event: str, callback: Callable[[str, dict[str, str]], None]
    ) -> None:
        """Remove event listener."""
        _LOGGER.info("Unregistered event %s for door %s", event, self.name)
        self._event_listeners[event].discard(callback)

    async def trigger_event(self, event: str, data: dict[str, str]):
        """Trigger event."""
        _LOGGER.info(
            "Triggering event %s for door %s with data %s",
            event,
            self.name,
            data,
        )
        for callback in self._event_listeners[event]:
            callback(data["type"], data)
            _LOGGER.info(
                "Event %s type %s for door %s fired", event, data["type"], self.name
            )

    def __eq__(self, value) -> bool:
        """Check if two doors are equal."""
        if isinstance(value, UnifiAccessDoor):
            return (
                self.id == value.id
                and self.name == value.name
                and self.hub_type == value.hub_type
                and self.door_position_status == value.door_position_status
                and self.door_lock_relay_status == value.door_lock_relay_status
                and self.lock_rule == value.lock_rule
                and self.lock_rule_ended_time == value.lock_rule_ended_time
            )
        return False

    def __repr__(self):
        """Return string representation of door."""
        return f"<UnifiAccessDoor id={self.id} name={self.name} hub_type={self.hub_type} door_position_status={self.door_position_status} door_lock_relay_status={self.door_lock_relay_status} lock_rule={self.lock_rule} lock_rule_ended_time={self.lock_rule_ended_time}>"

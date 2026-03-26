"""Unifi Access Hub.

Manages door state, websocket event handling, and update notifications
for the Home Assistant integration.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import time
from typing import Any
import unicodedata

from unifi_access_api import (
    ApiError,
    ApiNotFoundError,
    BaseInfo,
    DeviceUpdate,
    Door,
    DoorLockRelayStatus,
    DoorLockRule,
    DoorLockRuleType,
    DoorPositionStatus,
    EmergencyStatus,
    HwDoorbell,
    InsightsAdd,
    LocationUpdateLegacy,
    LocationUpdateV2,
    LogAdd,
    RemoteUnlock,
    RemoteView,
    RemoteViewChange,
    SettingUpdate,
    UnifiAccessApiClient,
    V2DeviceUpdate,
    V2LocationUpdate,
    WsMessageHandler,
)
from unifi_access_api.models.websocket import WebsocketMessage

from .const import (
    ACCESS_ENTRY_EVENT,
    ACCESS_EXIT_EVENT,
    ACCESS_GENERIC_EVENT,
    DOORBELL_START_EVENT,
    DOORBELL_STOP_EVENT,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize a door name using NFC normalization."""
    if not name:
        return ""
    return unicodedata.normalize("NFC", name.strip())


EventListener = Callable[[str, dict[str, str]], None]


@dataclass
class DoorState:
    """Mutable runtime state for a single door."""

    door: Door
    hub_id: str | None = None
    hub_type: str | None = None
    lock_rule: str = ""
    lock_rule_ended_time: int = 0
    lock_rule_interval: int = 10
    doorbell_request_id: str | None = None
    thumbnail: bytes | None = None
    thumbnail_last_updated: datetime | None = None

    _event_listeners: dict[str, list[EventListener]] = field(
        default_factory=dict, repr=False
    )

    @property
    def id(self) -> str:
        """Return the door id."""
        return str(self.door.id)

    @property
    def name(self) -> str:
        """Return the door name."""
        return str(self.door.name)

    @property
    def door_position_status(self) -> DoorPositionStatus:
        """Return the door position status."""
        return self.door.door_position_status

    @property
    def door_lock_relay_status(self) -> DoorLockRelayStatus:
        """Return the door lock relay status."""
        return self.door.door_lock_relay_status

    @property
    def is_locked(self) -> bool:
        """Return whether the door is locked."""
        return bool(self.door.door_lock_relay_status == DoorLockRelayStatus.LOCK)

    @property
    def is_open(self) -> bool:
        """Return whether the door is open."""
        return bool(self.door.door_position_status == DoorPositionStatus.OPEN)

    @property
    def doorbell_pressed(self) -> bool:
        """Return whether the doorbell is currently pressed."""
        return self.doorbell_request_id is not None

    def add_event_listener(self, event: str, listener: EventListener) -> None:
        """Add an event listener."""
        self._event_listeners.setdefault(event, []).append(listener)

    def remove_event_listener(self, event: str, listener: EventListener) -> None:
        """Remove an event listener."""
        listeners = self._event_listeners.get(event)
        if listeners and listener in listeners:
            listeners.remove(listener)

    def trigger_event(self, event: str, attributes: dict[str, str]) -> None:
        """Trigger all listeners for a given event."""
        for listener in self._event_listeners.get(event, []):
            listener(event, attributes)


class UnifiAccessHub:
    """Manages door state and websocket events on top of the async API client."""

    def __init__(
        self,
        client: UnifiAccessApiClient,
        *,
        use_polling: bool = False,
    ) -> None:
        """Initialize the hub."""
        self.client = client
        self.use_polling = use_polling
        self.doors: dict[str, DoorState] = {}
        self.evacuation: bool = False
        self.lockdown: bool = False
        self.supports_door_lock_rules: bool = True

        # Dedup: track last insights.add timestamp per door to suppress
        # redundant logs.add events when a hub sends both.
        self._last_insight_time: dict[str, float] = {}

        # Set by __init__.py after coordinator creation to push WS updates.
        self.on_doors_updated: Callable[[], None] | None = None
        self.on_emergency_updated: Callable[[], None] | None = None
        self.create_task: Callable[[Coroutine[Any, Any, None]], Any] | None = None

    def _notify_doors_updated(self) -> None:
        """Notify that door state changed (triggers coordinator update)."""
        if self.on_doors_updated:
            self.on_doors_updated()

    def _notify_emergency_updated(self) -> None:
        """Notify that emergency state changed (triggers coordinator update)."""
        if self.on_emergency_updated:
            self.on_emergency_updated()

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    async def async_update(self) -> dict[str, DoorState]:
        """Fetch all doors and return the door state dict (for coordinator)."""
        api_doors = await self.client.get_doors()
        for api_door in api_doors:
            if api_door.id in self.doors:
                self.doors[api_door.id].door = api_door
            else:
                self.doors[api_door.id] = DoorState(door=api_door)
        # Fetch lock rules for each door
        for door_id, state in self.doors.items():
            try:
                rule_status = await self.client.get_door_lock_rule(door_id)
                state.lock_rule = rule_status.type.value
                state.lock_rule_ended_time = rule_status.ended_time
            except ApiNotFoundError:
                _LOGGER.debug("Door lock rules not supported for door %s", door_id)
                self.supports_door_lock_rules = False
                break
        return self.doors

    async def async_get_emergency_status(self) -> EmergencyStatus:
        """Fetch the current emergency status."""
        status = await self.client.get_emergency_status()
        self.evacuation = status.evacuation
        self.lockdown = status.lockdown
        return status

    async def async_set_emergency_status(
        self, *, evacuation: bool | None = None, lockdown: bool | None = None
    ) -> None:
        """Set the emergency status."""
        current = await self.client.get_emergency_status()
        new_status = EmergencyStatus(
            evacuation=evacuation if evacuation is not None else current.evacuation,
            lockdown=lockdown if lockdown is not None else current.lockdown,
        )
        await self.client.set_emergency_status(new_status)
        self.evacuation = new_status.evacuation
        self.lockdown = new_status.lockdown
        self._notify_emergency_updated()

    async def async_set_lock_rule(self, door_id: str, rule_type: str) -> None:
        """Set a door lock rule."""
        if not rule_type:
            return

        state = self.doors.get(door_id)
        interval = state.lock_rule_interval if state else 0

        try:
            door_lock_rule_type = DoorLockRuleType(rule_type)
        except ValueError:
            _LOGGER.warning(
                "Unsupported door lock rule type '%s' for door %s",
                rule_type,
                door_id,
            )
            return

        rule = DoorLockRule(type=door_lock_rule_type, interval=interval)
        await self.client.set_door_lock_rule(door_id, rule)

        if state is not None:
            state.lock_rule = rule_type
            self._notify_doors_updated()

    # ------------------------------------------------------------------
    # WebSocket
    # ------------------------------------------------------------------

    def start_websocket(
        self,
        on_connect: Callable[[], Any] | None = None,
        on_disconnect: Callable[[], Any] | None = None,
    ) -> None:
        """Start the websocket connection with all event handlers."""
        handlers: dict[str, WsMessageHandler] = {
            "access.data.device.location_update_v2": self._handle_location_update,
            "access.data.v2.location.update": self._handle_v2_location_update,
            "access.data.location.update": self._handle_location_update_legacy,
            "access.data.v2.device.update": self._handle_v2_device_update,
            "access.logs.insights.add": self._handle_insights_add,
            "access.base.info": self._handle_base_info,
            "access.remote_view": self._handle_remote_view,
            "access.remote_view.change": self._handle_remote_view_change,
            "access.data.device.update": self._handle_device_update,
            "access.logs.add": self._handle_logs_add,
            "access.hw.door_bell": self._handle_hw_door_bell,
            "access.data.setting.update": self._handle_settings_update,
            "access.data.device.remote_unlock": self._handle_remote_unlock,
        }
        self.client.start_websocket(
            handlers,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
        )

    async def async_close(self) -> None:
        """Close the API client (stops websocket)."""
        await self.client.close()

    # ------------------------------------------------------------------
    # WebSocket helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_lock_dps(
        state: DoorState, *, dps: DoorPositionStatus, lock: str
    ) -> None:
        """Apply lock relay and door position updates to a door state."""
        updates: dict[str, DoorPositionStatus | DoorLockRelayStatus] = {
            "door_position_status": dps,
        }
        if lock == "locked":
            updates["door_lock_relay_status"] = DoorLockRelayStatus.LOCK
        elif lock == "unlocked":
            updates["door_lock_relay_status"] = DoorLockRelayStatus.UNLOCK
        state.door = state.door.with_updates(**updates)

    # ------------------------------------------------------------------
    # WebSocket handlers
    # ------------------------------------------------------------------

    async def _handle_location_update(self, msg: WebsocketMessage) -> None:
        """Handle location_update_v2 messages."""
        update: LocationUpdateV2 = msg  # type: ignore[assignment]
        door_id = update.data.id

        state = self.doors.get(door_id)
        if state is None:
            return

        # Update door with fields from the websocket
        ws_state = update.data.state
        if ws_state is not None:
            self._apply_lock_dps(state, dps=ws_state.dps, lock=ws_state.lock)

            state.lock_rule = ""
            state.lock_rule_ended_time = 0
            if ws_state.remain_lock is not None:
                state.lock_rule = ws_state.remain_lock.type.value
                state.lock_rule_ended_time = ws_state.remain_lock.until
            elif ws_state.remain_unlock is not None:
                state.lock_rule = ws_state.remain_unlock.type.value
                state.lock_rule_ended_time = ws_state.remain_unlock.until

        # Handle thumbnail
        if update.data.thumbnail is not None:
            thumb_url = update.data.thumbnail.url
            try:
                state.thumbnail = await self.client.get_thumbnail(thumb_url)
                state.thumbnail_last_updated = datetime.fromtimestamp(
                    update.data.thumbnail.door_thumbnail_last_update, tz=UTC
                )
            except (ApiError, TimeoutError):
                _LOGGER.debug("Failed to fetch thumbnail for door %s", door_id)

        _LOGGER.info(
            "Location update V2 door %s (%s): locked=%s dps=%s rule=%s",
            state.name,
            state.id,
            state.door_lock_relay_status,
            state.door_position_status,
            state.lock_rule,
        )
        self._notify_doors_updated()

    async def _handle_remote_view(self, msg: WebsocketMessage) -> None:
        """Handle remote_view (doorbell press start) messages."""
        update: RemoteView = msg  # type: ignore[assignment]
        door_name = update.data.door_name
        normalized = _normalize_name(door_name)

        state = next(
            (s for s in self.doors.values() if _normalize_name(s.name) == normalized),
            None,
        )
        if state is None:
            _LOGGER.warning("Could not find door with name '%s'", door_name)
            return

        state.doorbell_request_id = update.data.request_id
        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "type": DOORBELL_START_EVENT,
        }
        _LOGGER.info(
            "Doorbell press on %s request id %s",
            door_name,
            update.data.request_id,
        )
        self._notify_doors_updated()
        state.trigger_event("doorbell_press", event_attributes)

    async def _handle_remote_view_change(self, msg: WebsocketMessage) -> None:
        """Handle remote_view.change (doorbell press stop) messages."""
        update: RemoteViewChange = msg  # type: ignore[assignment]
        request_id = update.data.remote_call_request_id

        state = next(
            (s for s in self.doors.values() if s.doorbell_request_id == request_id),
            None,
        )
        if state is None:
            return

        state.doorbell_request_id = None
        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "type": DOORBELL_STOP_EVENT,
        }
        _LOGGER.info("Doorbell press stopped on %s", state.name)
        self._notify_doors_updated()
        state.trigger_event("doorbell_press", event_attributes)

    async def _handle_device_update(self, msg: WebsocketMessage) -> None:
        """Handle device update messages."""
        update: DeviceUpdate = msg  # type: ignore[assignment]
        device_id = update.data.unique_id
        device_type = update.data.device_type
        door_id = update.data.door.unique_id if update.data.door else None

        if door_id and door_id in self.doors:
            state = self.doors[door_id]
            if state.hub_id is None:
                state.hub_type = device_type
                state.hub_id = device_id
                _LOGGER.debug(
                    "Door %s (%s) associated with hub %s (%s)",
                    state.name,
                    state.id,
                    device_type,
                    device_id,
                )
                self._notify_doors_updated()

    async def _handle_logs_add(self, msg: WebsocketMessage) -> None:
        """Handle access log messages.

        Fires access events as a fallback for hubs that send ``logs.add``
        but not ``insights.add``.
        """
        update: LogAdd = msg  # type: ignore[assignment]
        source = update.data.source

        door_target = next((t for t in source.target if t.type == "door"), None)
        if door_target is None:
            return

        _LOGGER.debug(
            "Log add for door %s: %s by %s (%s)",
            door_target.id,
            source.event.result,
            source.actor.display_name,
            source.authentication.credential_provider,
        )

        # Fire access events from logs.add as fallback — but skip if
        # insights.add already fired for this door recently.
        last_insight = self._last_insight_time.get(door_target.id, 0.0)
        if time.monotonic() - last_insight < 5.0:
            return

        device_config = source.device_config
        if device_config is None:
            return

        state = self.doors.get(door_target.id)
        if state is None:
            _LOGGER.debug(
                "Potential buggy version of unifi access api detected - looking for door by hub id %s",
                door_target.id,
            )
            state = next(
                (
                    door
                    for door in self.doors.values()
                    if getattr(door, "hub_id", None) == door_target.id
                ),
                None,
            )
            if state is None:
                _LOGGER.warning(
                    "Could not find door for log event with door id %s (or hub id)",
                    door_target.id,
                )
                return

        access_type = device_config.display_name.lower()
        if access_type == "entry":
            event_type = ACCESS_ENTRY_EVENT
        elif access_type == "exit":
            event_type = ACCESS_EXIT_EVENT
        else:
            event_type = ACCESS_GENERIC_EVENT

        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "actor": source.actor.display_name,
            "authentication": source.authentication.credential_provider,
            "type": event_type,
            "result": source.event.result,
        }
        state.trigger_event("access", event_attributes)

    async def _handle_hw_door_bell(self, msg: WebsocketMessage) -> None:
        """Handle hardware doorbell press messages."""
        update: HwDoorbell = msg  # type: ignore[assignment]
        door_id = update.data.door_id
        door_name = update.data.door_name

        state = self.doors.get(door_id)
        if state is None:
            return

        state.doorbell_request_id = update.data.request_id
        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "type": DOORBELL_START_EVENT,
        }
        _LOGGER.info("Hardware doorbell press on %s (%s)", door_name, door_id)
        self._notify_doors_updated()
        state.trigger_event("doorbell_press", event_attributes)

        # Schedule automatic stop after 2 seconds
        captured_request_id = update.data.request_id

        async def _auto_stop() -> None:
            await asyncio.sleep(2)
            if state.doorbell_request_id != captured_request_id:
                return
            state.doorbell_request_id = None
            stop_attrs = {
                "door_name": state.name,
                "door_id": state.id,
                "type": DOORBELL_STOP_EVENT,
            }
            self._notify_doors_updated()
            state.trigger_event("doorbell_press", stop_attrs)

        if self.create_task:
            self.create_task(_auto_stop())
        else:
            _LOGGER.warning("Cannot schedule doorbell auto-stop: create_task not set")

    async def _handle_insights_add(self, msg: WebsocketMessage) -> None:
        """Handle insights add (access entry/exit) events."""
        update: InsightsAdd = msg  # type: ignore[assignment]
        door_entries = update.data.metadata.door
        if not door_entries:
            _LOGGER.debug("Ignoring insights event without door metadata: %s", update)
            return
        reported_door_id = door_entries[0].id
        state = self.doors.get(reported_door_id)
        if state is None:
            _LOGGER.debug(
                "Potential buggy version of unifi access api detected - looking for door by hub id %s",
                reported_door_id,
            )
            state = next(
                (
                    door
                    for door in self.doors.values()
                    if getattr(door, "hub_id", None) == reported_door_id
                ),
                None,
            )
            if state is None:
                _LOGGER.warning(
                    "Could not find door for insights event with door id %s (or hub id)",
                    reported_door_id,
                )
                return

        canonical_door_id = state.id

        direction_entries = update.data.metadata.opened_direction
        direction = (
            direction_entries[0].display_name.lower() if direction_entries else ""
        )
        if direction == "entry":
            event_type = ACCESS_ENTRY_EVENT
        elif direction == "exit":
            event_type = ACCESS_EXIT_EVENT
        else:
            event_type = ACCESS_GENERIC_EVENT

        method_entries = update.data.metadata.opened_method
        method = method_entries[0].display_name if method_entries else ""

        event_attributes = {
            "door_name": state.name,
            "door_id": state.id,
            "actor": update.data.metadata.actor.display_name,
            "authentication": update.data.metadata.authentication.display_name,
            "type": event_type,
            "method": method,
            "result": update.data.result,
        }
        _LOGGER.info(
            "Insight: %s on %s (%s) by %s via %s: %s",
            update.data.event_type,
            state.name,
            state.id,
            update.data.metadata.actor.display_name,
            update.data.metadata.authentication.display_name,
            update.data.result,
        )
        self._last_insight_time[canonical_door_id] = time.monotonic()
        state.trigger_event("access", event_attributes)

    async def _handle_v2_location_update(self, msg: WebsocketMessage) -> None:
        """Handle V2 location update messages."""
        update: V2LocationUpdate = msg  # type: ignore[assignment]
        door_id = update.data.id

        state = self.doors.get(door_id)
        if state is None:
            return

        ws_state = update.data.state
        if ws_state is not None:
            self._apply_lock_dps(state, dps=ws_state.dps, lock=ws_state.lock)

            # Lock rules
            state.lock_rule = ""
            state.lock_rule_ended_time = 0
            if ws_state.remain_lock is not None:
                state.lock_rule = ws_state.remain_lock.type.value
                state.lock_rule_ended_time = ws_state.remain_lock.until
            elif ws_state.remain_unlock is not None:
                state.lock_rule = ws_state.remain_unlock.type.value
                state.lock_rule_ended_time = ws_state.remain_unlock.until

        # Handle thumbnail
        if update.data.thumbnail is not None:
            thumb_url = update.data.thumbnail.url
            try:
                state.thumbnail = await self.client.get_thumbnail(thumb_url)
                state.thumbnail_last_updated = datetime.fromtimestamp(
                    update.data.thumbnail.door_thumbnail_last_update, tz=UTC
                )
            except (ApiError, TimeoutError):
                _LOGGER.debug("Failed to fetch thumbnail for door %s", door_id)

        _LOGGER.info(
            "V2 location update door %s (%s): locked=%s dps=%s rule=%s",
            state.name,
            state.id,
            state.door_lock_relay_status,
            state.door_position_status,
            state.lock_rule,
        )
        self._notify_doors_updated()

    async def _handle_v2_device_update(self, msg: WebsocketMessage) -> None:
        """Handle V2 device update messages."""
        update: V2DeviceUpdate = msg  # type: ignore[assignment]
        device_id = update.data.id
        device_type = update.data.device_type

        updated = False
        for loc_state in update.data.location_states:
            door_id = loc_state.location_id
            state = self.doors.get(door_id)
            if state is None:
                continue

            if state.hub_id is None:
                state.hub_type = device_type
                state.hub_id = device_id

            self._apply_lock_dps(state, dps=loc_state.dps, lock=loc_state.lock)

            # Lock rules
            state.lock_rule = ""
            state.lock_rule_ended_time = 0
            if loc_state.remain_lock is not None:
                state.lock_rule = loc_state.remain_lock.type.value
                state.lock_rule_ended_time = loc_state.remain_lock.until
            elif loc_state.remain_unlock is not None:
                state.lock_rule = loc_state.remain_unlock.type.value
                state.lock_rule_ended_time = loc_state.remain_unlock.until

            updated = True

        _LOGGER.debug(
            "V2 device update %s (%s): online=%s firmware=%s",
            update.data.alias or update.data.name,
            device_id,
            update.data.online,
            update.data.firmware,
        )
        if updated:
            self._notify_doors_updated()

    async def _handle_location_update_legacy(self, msg: WebsocketMessage) -> None:
        """Handle legacy (V1) location update messages."""
        update: LocationUpdateLegacy = msg  # type: ignore[assignment]
        door_id = update.data.unique_id

        state = self.doors.get(door_id)
        if state is None:
            return

        updated = False
        extras = update.data.extras
        if extras is not None:
            thumb_url = extras.get("door_thumbnail")
            thumb_ts = extras.get("door_thumbnail_last_update")
            if thumb_url and isinstance(thumb_url, str):
                try:
                    state.thumbnail = await self.client.get_thumbnail(thumb_url)
                    if thumb_ts is not None:
                        state.thumbnail_last_updated = datetime.fromtimestamp(
                            int(thumb_ts), tz=UTC
                        )
                    updated = True
                except (ApiError, TimeoutError, ValueError):
                    _LOGGER.debug("Failed to fetch thumbnail for door %s", door_id)

        _LOGGER.debug(
            "Legacy location update door %s (%s)",
            state.name,
            state.id,
        )
        if updated:
            self._notify_doors_updated()

    async def _handle_base_info(self, msg: WebsocketMessage) -> None:
        """Handle base info (log counter) messages."""
        update: BaseInfo = msg  # type: ignore[assignment]
        _LOGGER.debug("Base info: top_log_count=%s", update.data.top_log_count)

    async def _handle_settings_update(self, msg: WebsocketMessage) -> None:
        """Handle settings update (evacuation/lockdown) messages."""
        update: SettingUpdate = msg  # type: ignore[assignment]
        self.evacuation = update.data.evacuation
        self.lockdown = update.data.lockdown
        _LOGGER.info(
            "Settings updated: evacuation=%s lockdown=%s",
            self.evacuation,
            self.lockdown,
        )
        self._notify_emergency_updated()

    async def _handle_remote_unlock(self, msg: WebsocketMessage) -> None:
        """Handle remote door unlock messages."""
        update: RemoteUnlock = msg  # type: ignore[assignment]
        door_id = update.data.unique_id

        state = self.doors.get(door_id)
        if state is None:
            return

        state.door = state.door.with_updates(
            door_lock_relay_status=DoorLockRelayStatus.UNLOCK
        )
        _LOGGER.info("Remote unlock on %s (%s)", state.name, state.id)
        self._notify_doors_updated()

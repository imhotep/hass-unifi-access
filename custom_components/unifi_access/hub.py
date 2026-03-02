"""Unifi Access Hub.

This module interacts with the Unifi Access API server.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from unifi_access_api import UnifiAccessApiClient, UnifiAccessDoor, normalize_door_name

from .const import ACCESS_EVENT, DOORBELL_START_EVENT, DOORBELL_STOP_EVENT

_LOGGER = logging.getLogger(__name__)


class UnifiAccessHub(UnifiAccessApiClient):
    """Unifi Access Hub.

    This class takes care of interacting with the Unifi Access API.
    """

    def __init__(
        self, host: str, verify_ssl: bool = False, use_polling: bool = False
    ) -> None:
        """Initialize the UnifiAccessHub.

        Args:
            host: Hostname or address of the Unifi Access server.
            verify_ssl: Whether to verify SSL certificates.
            use_polling: Whether to use polling instead of websocket push.
        """
        super().__init__(host, verify_ssl=verify_ssl, use_polling=use_polling)
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default websocket event handlers on the API client.

        This wires the known Unifi Access websocket event names to the
        corresponding handler methods on this class.
        """
        handlers = {
            "access.data.v2.location.update": self._handle_access_location_update,
            "access.remote_view": self._handle_remote_view,
            "access.remote_view.change": self._handle_remote_view_change,
            "access.data.device.update": self._handle_device_update,
            "access.logs.add": self._handle_logs_add,
            "access.hw.door_bell": self._handle_hw_door_bell,
            "access.data.setting.update": self._handle_settings_update,
        }
        for event, handler in handlers.items():
            self.register_websocket_handler(event, handler)

    def _publish_door_update(
        self,
        door: UnifiAccessDoor | None,
        event: str | None = None,
        event_attributes: dict[str, Any] | None = None,
        event_done_callback=None,
    ) -> None:
        """Publish updates and optionally trigger an event for a door.

        If `door` is None this is a no-op. Otherwise the door's
        `publish_updates` coroutine is scheduled on the hub loop. If an
        `event` and `event_attributes` are provided, `door.trigger_event`
        is scheduled and the optional `event_done_callback` is attached to
        the returned future.

        Args:
            door: Door object to update.
            event: Optional event name to trigger on the door.
            event_attributes: Attributes to include with the triggered event.
            event_done_callback: Optional callback to run when the event task
                completes. Can be a coroutine function.
        """
        if not door:
            return

        asyncio.run_coroutine_threadsafe(door.publish_updates(), self.loop)
        if event is not None and event_attributes is not None:
            task = asyncio.run_coroutine_threadsafe(
                door.trigger_event(event, event_attributes),
                self.loop,
            )
            if event_done_callback is not None:
                task.add_done_callback(event_done_callback)

    def _handle_access_location_update(self, update: dict[str, Any]) -> None:
        """Handle an `access.data.v2.location.update` websocket message.

        Calls into the underlying library to apply the location update and
        publishes a door update if a door was modified.
        """
        existing_door = self._handle_location_update_v2(update)
        if existing_door:
            _LOGGER.info(
                "Location update V2 door name %s with id %s config updated. locked: %s dps: %s, lock rule: %s, lock rule ended time %s",
                existing_door.name,
                existing_door.id,
                existing_door.door_lock_relay_status,
                existing_door.door_position_status,
                existing_door.lock_rule,
                existing_door.lock_rule_ended_time,
            )
        self._publish_door_update(existing_door)

    def _handle_remote_view(self, update: dict[str, Any]) -> None:
        """Handle a remote view (doorbell press) websocket message.

        The message contains the door name and a request id. This locates
        the matching door and publishes a doorbell start event.
        """
        door_name = update["data"]["door_name"]
        _LOGGER.debug("access.remote_view %s", door_name)
        normalized_door_name = normalize_door_name(door_name)
        _LOGGER.debug(
            "Normalized door name from websocket: '%s' -> '%s'",
            door_name,
            normalized_door_name,
        )
        existing_door = next(
            (
                door
                for door in self.doors.values()
                if normalize_door_name(door.name) == normalized_door_name
            ),
            None,
        )
        if existing_door is None:
            _LOGGER.warning(
                "Could not find door with normalized name '%s'. Available doors: %s",
                normalized_door_name,
                [
                    f"'{door.name}' (normalized: '{normalize_door_name(door.name)}')"
                    for door in self.doors.values()
                ],
            )
            return

        existing_door.doorbell_request_id = update["data"]["request_id"]
        event_attributes = {
            "door_name": existing_door.name,
            "door_id": existing_door.id,
            "type": DOORBELL_START_EVENT,
        }
        _LOGGER.info(
            "Doorbell press on %s request id %s",
            door_name,
            update["data"]["request_id"],
        )
        self._publish_door_update(
            existing_door, event="doorbell_press", event_attributes=event_attributes
        )

    def _handle_remote_view_change(self, update: dict[str, Any]) -> None:
        """Handle a remote view change (doorbell stop) websocket message.

        Matches the request id to an existing door and publishes a stop
        event for the doorbell press.
        """
        doorbell_request_id = update["data"]["remote_call_request_id"]
        _LOGGER.debug("access.remote_view.change request id %s", doorbell_request_id)
        existing_door = next(
            (
                door
                for door in self.doors.values()
                if door.doorbell_request_id == doorbell_request_id
            ),
            None,
        )
        if existing_door is None:
            return

        existing_door.doorbell_request_id = None
        event_attributes = {
            "door_name": existing_door.name,
            "door_id": existing_door.id,
            "type": DOORBELL_STOP_EVENT,
        }
        _LOGGER.info(
            "Doorbell press stopped on %s request id %s",
            existing_door.name,
            doorbell_request_id,
        )
        self._publish_door_update(
            existing_door, event="doorbell_press", event_attributes=event_attributes
        )

    def _handle_device_update(self, update: dict[str, Any]) -> None:
        """Handle a device update websocket message.

        Associates a device with a door when the device reports its linked
        door id and updates the stored hub id/type on the door object.
        """
        _LOGGER.debug("access.data.device.update: device type %s", update["data"])
        device_id = update["data"]["unique_id"]
        device_type = update["data"]["device_type"]
        door_id = update["data"].get("door", {}).get("unique_id")
        if door_id in self.doors and self.doors[door_id].hub_id is None:
            existing_door = self.doors[door_id]
            existing_door.hub_type = device_type
            existing_door.hub_id = device_id
            _LOGGER.debug(
                "Door name %s door id %s is now associated with hub type %s hub id %s",
                existing_door.name,
                existing_door.id,
                existing_door.hub_type,
                existing_door.hub_id,
            )
            self._publish_door_update(existing_door)

    def _handle_logs_add(self, update: dict[str, Any]) -> None:
        """Handle an access log entry websocket message.

        Extracts actor and authentication information and publishes an
        ACCESS_EVENT for the affected door when possible.
        """
        _LOGGER.debug("access.logs.add %s", update["data"])
        door = next(
            (
                target
                for target in update["data"]["_source"]["target"]
                if target["type"] == "door"
            ),
            None,
        )
        if door is None:
            return

        door_id = door.get("id")
        existing_door = self.doors.get(door_id)
        if existing_door is None:
            _LOGGER.debug(
                "Buggy version of unifi access api detected - looking for door by hub id %s",
                door_id,
            )
            existing_door = next(
                (
                    door
                    for door in self.doors.values()
                    if getattr(door, "hub_id", None) == door_id
                ),
                None,
            )
        if existing_door is None:
            return

        _LOGGER.debug(
            "access log added for door id %s, hub id %s",
            existing_door.id,
            existing_door.hub_id,
        )
        actor = update["data"]["_source"]["actor"]["display_name"]
        result = update["data"]["_source"]["event"]["result"]
        authentication = update["data"]["_source"]["authentication"][
            "credential_provider"
        ]
        device_config = next(
            (
                target
                for target in update["data"]["_source"]["target"]
                if target["type"] == "device_config"
            ),
            None,
        )
        if device_config is None:
            return

        access_type = device_config["display_name"]
        event_attributes = {
            "door_name": existing_door.name,
            "door_id": existing_door.id,
            "actor": actor,
            "authentication": authentication,
            "type": ACCESS_EVENT.format(type=access_type),
            "result": result,
        }
        _LOGGER.info(
            "Door name %s with id %s accessed by %s. authentication %s, access type: %s, result: %s",
            existing_door.name,
            existing_door.id,
            actor,
            authentication,
            access_type,
            result,
        )
        self._publish_door_update(
            existing_door, event="access", event_attributes=event_attributes
        )

    def _handle_hw_door_bell(self, update: dict[str, Any]) -> None:
        """Handle a hardware doorbell press message.

        Triggers a doorbell start event immediately and schedules a
        delayed stop event via the optional `on_complete` callback.
        """
        door_id = update["data"]["door_id"]
        door_name = update["data"]["door_name"]
        _LOGGER.info(
            "Hardware Doorbell Press %s door id %s",
            door_name,
            door_id,
        )
        if door_id not in self.doors:
            return

        existing_door = self.doors[door_id]
        existing_door.doorbell_request_id = update["data"]["request_id"]
        event_attributes = {
            "door_name": existing_door.name,
            "door_id": existing_door.id,
            "type": DOORBELL_START_EVENT,
        }

        async def on_complete(_fut):
            existing_door.doorbell_request_id = None
            event_attributes_stop = {
                "door_name": existing_door.name,
                "door_id": existing_door.id,
                "type": DOORBELL_STOP_EVENT,
            }
            await asyncio.sleep(2)
            await existing_door.trigger_event("doorbell_press", event_attributes_stop)

        _LOGGER.info(
            "Hardware doorbell press on %s request id %s",
            door_name,
            update["data"]["request_id"],
        )
        self._publish_door_update(
            existing_door,
            event="doorbell_press",
            event_attributes=event_attributes,
            event_done_callback=on_complete,
        )

    def _handle_settings_update(self, update: dict[str, Any]) -> None:
        """Handle settings update messages.

        Updates evacuation and lockdown state and triggers a publish of
        the hub state to listeners.
        """
        self.evacuation = update["data"]["evacuation"]
        self.lockdown = update["data"]["lockdown"]
        asyncio.run_coroutine_threadsafe(self.publish_updates(), self.loop)
        _LOGGER.info(
            "Settings updated. Evacuation %s, Lockdown %s",
            self.evacuation,
            self.lockdown,
        )


__all__ = ["UnifiAccessHub"]

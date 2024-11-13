"""Unifi Access Hub.

This module interacts with the Unifi Access API server.
"""

import asyncio
from collections.abc import Callable
import json
import logging
import ssl
from threading import Thread
from typing import Any, Literal, TypedDict, cast
from urllib.parse import urlparse

from requests import request
from requests.exceptions import ConnectionError as ConnError, SSLError
import urllib3
import websocket

from .const import (
    ACCESS_EVENT,
    DEVICE_NOTIFICATIONS_URL,
    DOOR_LOCK_RULE_URL,
    DOOR_UNLOCK_URL,
    DOORBELL_START_EVENT,
    DOORBELL_STOP_EVENT,
    DOORS_EMERGENCY_URL,
    DOORS_URL,
    UNIFI_ACCESS_API_PORT,
)
from .door import UnifiAccessDoor
from .errors import ApiAuthError, ApiError

_LOGGER = logging.getLogger(__name__)

type EmergencyData = dict[str, bool]


class DoorLockRule(TypedDict):
    """DoorLockRule.

    This class defines the different locking rules.
    """

    type: Literal["keep_lock", "keep_unlock", "custom", "reset", "lock_early"]
    interval: int


class DoorLockRuleStatus(TypedDict):
    """DoorLockRuleStatus.

    This class defines the active locking rule status.
    """

    type: Literal["schedule", "keep_lock", "keep_unlock", "custom", "lock_early", ""]
    ended_time: int


class UnifiAccessHub:
    """UnifiAccessHub.

    This class takes care of interacting with the Unifi Access API.
    """

    def __init__(
        self, host: str, verify_ssl: bool = False, use_polling: bool = False
    ) -> None:
        """Initialize."""
        self.use_polling = use_polling
        self.verify_ssl = verify_ssl
        if self.verify_ssl is False:
            _LOGGER.warning("SSL Verification disabled for %s", host)
            urllib3.disable_warnings()

        host_parts = host.split(":")
        parsed_host = urlparse(host)

        hostname = parsed_host.hostname if parsed_host.hostname else host_parts[0]
        port = (
            parsed_host.port
            if parsed_host.port
            else (host_parts[1] if len(host_parts) > 1 else UNIFI_ACCESS_API_PORT)
        )
        self._api_token = None
        self.host = f"https://{hostname}:{port}"
        self._http_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.websocket_host = f"wss://{hostname}:{port}"
        self._websocket_headers = {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
        }
        self._doors: dict[str, UnifiAccessDoor] = {}
        self.evacuation = False
        self.lockdown = False
        self.supports_door_lock_rules = True
        self.update_t = None
        self._callbacks: set[Callable] = set()
        self.loop = asyncio.get_event_loop()

    @property
    def doors(self):
        """Get current doors."""
        return self._doors

    def set_api_token(self, api_token):
        """Set API Access Token."""
        self._api_token = api_token
        self._http_headers["Authorization"] = f"Bearer {self._api_token}"
        self._websocket_headers["Authorization"] = f"Bearer {self._api_token}"

    def update(self):
        """Get latest door data."""
        _LOGGER.debug(
            "Getting door updates from Unifi Access %s Use Polling %s. Doors? %s",
            self.host,
            self.use_polling,
            self.doors,
        )
        data = self._make_http_request(f"{self.host}{DOORS_URL}")

        for _i, door in enumerate(data):
            door_id = door["id"]
            door_lock_rule = {"type": "", "ended_time": 0}
            if self.supports_door_lock_rules:
                door_lock_rule = self.get_door_lock_rule(door_id)
            if door_id in self.doors:
                existing_door = self.doors[door_id]
                existing_door.name = door["name"]
                existing_door.door_position_status = door["door_position_status"]
                existing_door.door_lock_relay_status = door["door_lock_relay_status"]
                existing_door.door_lock_rule = door_lock_rule["type"]
                existing_door.door_lock_ended_time = door_lock_rule["ended_time"]
            elif door["is_bind_hub"] is True:
                self._doors[door_id] = UnifiAccessDoor(
                    door_id=door["id"],
                    name=door["name"],
                    door_position_status=door["door_position_status"],
                    door_lock_relay_status=door["door_lock_relay_status"],
                    door_lock_rule=door_lock_rule["type"],
                    door_lock_rule_ended_time=door_lock_rule["ended_time"],
                    hub=self,
                )
        if self.update_t is None and self.use_polling is False:
            self.start_continuous_updates()

        return self._doors

    def update_door(self, door_id: int) -> None:
        """Get latest door data for a specific door."""
        _LOGGER.info("Getting door update from Unifi Access with id %s", door_id)
        updated_door = self._make_http_request(f"{self.host}{DOORS_URL}/{door_id}")
        door_id = updated_door["id"]
        _LOGGER.debug("got door update %s", updated_door)
        if door_id in self.doors:
            existing_door: UnifiAccessDoor = self.doors[door_id]
            existing_door.door_lock_relay_status = updated_door[
                "door_lock_relay_status"
            ]
            existing_door.door_position_status = updated_door["door_position_status"]
            existing_door.name = updated_door["name"]
            _LOGGER.debug("door %s updated", door_id)

    def authenticate(self, api_token: str) -> str:
        """Test if we can authenticate with the host."""
        self.set_api_token(api_token)
        _LOGGER.info("Authenticating %s", self.host)
        try:
            self.update()
        except ApiError:
            _LOGGER.error(
                "Could perform action with %s. Check host and token", self.host
            )
            return "api_error"
        except ApiAuthError:
            _LOGGER.error(
                "Could not authenticate with %s. Check host and token", self.host
            )
            return "api_auth_error"
        except SSLError:
            _LOGGER.error("Error validating SSL Certificate for %s", self.host)
            return "ssl_error"
        except ConnError:
            _LOGGER.error("Cannot connect to %s", self.host)
            return "cannot_connect"

        return "ok"

    def get_door_lock_rule(self, door_id: str) -> DoorLockRuleStatus:
        """Get door lock rule."""
        _LOGGER.debug("Getting door lock rule for door_id %s", door_id)
        try:
            data = self._make_http_request(
                f"{self.host}{DOOR_LOCK_RULE_URL}".format(door_id=door_id)
            )
            _LOGGER.debug("Got door lock rule for door_id %s %s", door_id, data)
            return cast(DoorLockRuleStatus, data)
        except (ApiError, KeyError):
            self.supports_door_lock_rules = False
            _LOGGER.debug("cannot get door lock rule. Likely unsupported hub")
            return {"type": "", "ended_time": 0}

    def set_door_lock_rule(self, door_id: str, door_lock_rule: DoorLockRule) -> None:
        """Set door lock rule."""
        _LOGGER.info(
            "Setting door lock rule for Door ID %s %s", door_id, door_lock_rule
        )
        self._make_http_request(
            f"{self.host}{DOOR_LOCK_RULE_URL}".format(door_id=door_id),
            "PUT",
            door_lock_rule,
        )
        self.doors[door_id].lock_rule = door_lock_rule["type"]
        if door_lock_rule["type"] == "custom":
            self.doors[door_id].interval = door_lock_rule["interval"]

    def get_doors_emergency_status(self) -> EmergencyData:
        """Get doors emergency status."""
        _LOGGER.debug("Getting doors emergency status")
        data = self._make_http_request(f"{self.host}{DOORS_EMERGENCY_URL}")
        self.evacuation = data["evacuation"]
        self.lockdown = data["lockdown"]
        _LOGGER.debug("Got doors emergency status %s", data)
        return data

    def set_doors_emergency_status(self, emergency_data: EmergencyData) -> None:
        """Set doors emergency status."""
        _LOGGER.info("Setting doors emergency status %s", emergency_data)
        self._make_http_request(
            f"{self.host}{DOORS_EMERGENCY_URL}", "PUT", emergency_data
        )
        self.evacuation = emergency_data.get("evacuation", self.evacuation)
        self.lockdown = emergency_data.get("lockdown", self.lockdown)
        _LOGGER.debug("Emergency status set %s", emergency_data)

    def unlock_door(self, door_id: str) -> None:
        """Test if we can authenticate with the host."""
        _LOGGER.info("Unlocking door with id %s", door_id)
        self._make_http_request(
            f"{self.host}{DOOR_UNLOCK_URL}".format(door_id=door_id), "PUT"
        )

    def _make_http_request(self, url, method="GET", data=None) -> dict:
        """Make HTTP request to Unifi Access API server."""
        _LOGGER.debug(
            "Making HTTP %s Request with URL %s and data %s", method, url, data
        )
        r = request(
            method,
            url,
            headers=self._http_headers,
            verify=self.verify_ssl,
            json=data,
            timeout=10,
        )

        if r.status_code == 401:
            raise ApiAuthError

        if r.status_code != 200:
            raise ApiError

        response = r.json()

        _LOGGER.debug("HTTP Response %s", response)

        return response["data"]

    def _handle_UAH_config_update(self, update, device_type):
        """Process UAH config update."""
        door_id = update["data"]["door"]["unique_id"]
        _LOGGER.debug(
            "access.data.device.update: door id %s, device type %s",
            door_id,
            device_type,
        )
        if door_id in self.doors:
            existing_door = self.doors[door_id]
            existing_door.hub_type = device_type
            _LOGGER.debug(
                "updating config for door name %s, id %s",
                existing_door.name,
                door_id,
            )
            existing_door.door_position_status = (
                "close"
                if next(
                    (
                        config["value"]
                        for config in update["data"]["configs"]
                        if config["key"] == "input_state_dps"
                    ),
                    "on",
                )
                == "on"
                else "open"
            )
            existing_door.door_lock_relay_status = (
                "unlock"
                if next(
                    (
                        config["value"]
                        for config in update["data"]["configs"]
                        if config["key"] == "input_state_rly-lock_dry"
                    ),
                    "off",
                )
                == "on"
                else "lock"
            )
            existing_door.lock_rule = next(
                (
                    config["value"]
                    for config in update["data"]["configs"]
                    # if config["key"] == "temp_lock_type"
                    if config["key"] == "lock_type"
                ),
                "",
            )
            existing_door.lock_rule_ended_time = next(
                (
                    config["value"]
                    for config in update["data"]["configs"]
                    if config["key"] == "lock_end_time"
                ),
                0,
            )
            return [existing_door]

    def _handle_UAH_Ent_config_update(self, update, device_type):
        """Process UAH-Ent config update."""
        # UAH-Ent has 8 ports
        # Port X dps = data.config[input_dX_dps], relay = data.config[output_dX_lock_relay]
        changed_doors = []
        for ext in update["data"]["extensions"]:
            door_id = ext["target_value"]
            # dev_id = ext["device_id"]
            existing_door = self.doors[door_id]
            existing_door.hub_type = device_type
            _LOGGER.debug(
                "access.data.device.update: door id %s, device type %s",
                door_id,
                device_type,
            )
            port = ext["source_id"].replace("port", "")
            poskey = f"input_d{port}_dps"
            relaykey = f"output_d{port}_lock_relay"
            existing_door.door_position_status = (
                "close"
                if next(
                    (
                        config["value"]
                        for config in update["data"]["configs"]
                        if config["key"] == poskey
                    ),
                    "off",
                )
                == "on"
                else "open"
            )
            existing_door.door_lock_relay_status = (
                "unlock"
                if next(
                    (
                        config["value"]
                        for config in update["data"]["configs"]
                        if config["key"] == relaykey
                    ),
                    "off",
                )
                == "on"
                else "lock"
            )
            changed_doors.append(existing_door)
            # TODO find config keys for temporary lock rules and their ended time # pylint: disable=fixme
        return changed_doors

    def _handle_UGT_config_update(self, update, device_type):
        """Process UGT config update."""
        # UGT has 2 ports
        # Port 1 = vehicle gate, dps = data.config[input_gate_dps], relay = data.config[output_oper1_relay || output_oper2_relay]
        # Port 2 = pedestrian gate, dps = data.config[input_door_dps], relay = data.config[output_door_lock_relay]
        changed_doors = []
        for ext in update["data"]["extensions"]:
            door_id = ext["target_value"]
            existing_door = self.doors[door_id]
            existing_door.hub_type = device_type
            _LOGGER.debug(
                "access.data.device.update: door id %s, device type %s",
                door_id,
                device_type,
            )
            # dev_id = ext["device_id"]
            port = ext["source_id"]
            dps_config_key = ""
            dlrs_config_key = ""
            if port == "port1":
                dps_config_key = "input_gate_dps"
                dlrs_config_key = "output_oper1_relay"
            elif port == "port2":
                dps_config_key = "input_door_dps"
                dlrs_config_key = "output_door_lock_relay"
            if dps_config_key and dlrs_config_key:
                existing_door.door_position_status = (
                    "close"
                    if next(
                        (
                            config["value"]
                            for config in update["data"]["configs"]
                            if config["key"] == dps_config_key
                        ),
                        "off",
                    )
                    == "on"
                    else "open"
                )
                existing_door.door_lock_relay_status = (
                    "unlock"
                    if next(
                        (
                            config["value"]
                            for config in update["data"]["configs"]
                            if config["key"] == dlrs_config_key
                        ),
                        "off",
                    )
                    == "on"
                    else "lock"
                )
            changed_doors.append(existing_door)
        return changed_doors

    def _handle_UNKNOWN_config_update(self, update, device_type):
        """Handle unknown hub types."""
        _LOGGER.critical("UniFi Access Hub type %s unknown", device_type)
        _LOGGER.critical("%s", update)

    def _handle_config_update(self, update, device_type):
        """Process config update."""
        match device_type:
            case "UAH":
                return self._handle_UAH_config_update(update, device_type)
            case "UAH-DOOR":
                return self._handle_UAH_config_update(update, device_type)
            case "UA-Intercom":
                return self._handle_UAH_config_update(update, device_type)
            case "UAH-Ent":
                return self._handle_UAH_Ent_config_update(update, device_type)
            case "UA-ULTRA":
                return self._handle_UAH_Ent_config_update(update, device_type)
            case "UGT":
                return self._handle_UGT_config_update(update, device_type)
            case _:
                return self._handle_UNKNOWN_config_update(update, device_type)

    def on_message(self, ws: websocket.WebSocketApp, message):  # noqa: C901
        """Handle messages received on the websocket client.

        Doorbell presses are relying on door names so if those are not unique, it may cause some issues
        """
        event = None
        event_attributes = None
        event_done_callback = None
        if "Hello" not in message:
            _LOGGER.debug("websocket message received %s", message)
            update = json.loads(message)
            existing_door = None
            changed_doors = []
            match update["event"]:
                case "access.dps_change":
                    door_id = update["data"]["door_id"]
                    _LOGGER.info("DPS update for door id %s", door_id)
                    if door_id in self.doors:
                        existing_door = self.doors[door_id]
                        existing_door.door_position_status = update["data"]["status"]
                        _LOGGER.info(
                            "DPS update for existing door %s with id %s status: %s",
                            existing_door.name,
                            door_id,
                            update["data"]["status"],
                        )
                        changed_doors.append(existing_door)
                case "access.data.device.remote_unlock":
                    door_id = update["data"]["unique_id"]
                    _LOGGER.info("Remote Unlock %s", door_id)
                    if door_id in self.doors:
                        existing_door = self.doors[door_id]
                        existing_door.door_lock_relay_status = "unlock"
                        _LOGGER.info(
                            "Remote unlock of door %s with id %s",
                            existing_door.name,
                            door_id,
                        )
                        changed_doors.append(existing_door)
                case "access.data.device.update":
                    device_type = update["data"]["device_type"]
                    door_updates = self._handle_config_update(update, device_type)
                    if door_updates:
                        changed_doors.extend(door_updates)
                        for door in door_updates:
                            _LOGGER.info(
                                "Device update on %s door name %s with id %s config updated. locked: %s dps: %s, lock rule: %s, lock rule ended time %s",
                                device_type,
                                door.name,
                                door.id,
                                door.door_lock_relay_status,
                                door.door_position_status,
                                door.lock_rule,
                                door.lock_rule_ended_time,
                            )

                case "access.remote_view":
                    door_name = update["data"]["door_name"]
                    _LOGGER.debug("access.remote_view %s", door_name)
                    existing_door = next(
                        (
                            door
                            for door in self.doors.values()
                            if door.name == door_name
                        ),
                        None,
                    )  # FIXME this is likely unreliable. API does not seem to provide door id forthis access.remote_view  # pylint: disable=fixme
                    if existing_door is not None:
                        existing_door.doorbell_request_id = update["data"]["request_id"]
                        event = "doorbell_press"
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
                        changed_doors.append(existing_door)
                case "access.remote_view.change":
                    doorbell_request_id = update["data"]["remote_call_request_id"]
                    _LOGGER.debug(
                        "access.remote_view.change request id %s", doorbell_request_id
                    )
                    existing_door = next(
                        (
                            door
                            for door in self.doors.values()
                            if door.doorbell_request_id == doorbell_request_id
                        ),
                        None,
                    )
                    if existing_door is not None:
                        existing_door.doorbell_request_id = None
                        event = "doorbell_press"
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
                        changed_doors.append(existing_door)
                case "access.logs.add":
                    _LOGGER.debug("access.logs.add %s", update["data"])
                    door = next(
                        (
                            target
                            for target in update["data"]["_source"]["target"]
                            if target["type"] == "door"
                        ),
                        None,
                    )
                    if door is not None:
                        door_id = door["id"]
                        _LOGGER.debug("access log added for door id %s", door_id)
                        if door_id in self.doors:
                            existing_door = self.doors[door_id]
                            actor = update["data"]["_source"]["actor"]["display_name"]
                            #"REMOTE_THROUGH_UAH" , "NFC" , "MOBILE_TAP" , "PIN_CODE"
                            authentication = update["data"]["_source"]["authentication"]["credential_provider"]
                            device_config = next(
                                (
                                    target
                                    for target in update["data"]["_source"]["target"]
                                    if target["type"] == "device_config"
                                ),
                                None,
                            )
                            if device_config is not None:
                                access_type = device_config["display_name"]
                                event = "access"
                                event_attributes = {
                                    "door_name": existing_door.name,
                                    "door_id": door_id,
                                    "actor": actor,
                                    "authentication": authentication,
                                    "type": ACCESS_EVENT.format(type=access_type),
                                }
                                _LOGGER.info(
                                    "Door name %s with id %s accessed by %s. authentication %s, access type: %s",
                                    existing_door.name,
                                    door_id,
                                    actor,
                                    authentication,
                                    access_type,
                                )
                            changed_doors.append(existing_door)
                case "access.hw.door_bell":
                    door_id = update["data"]["door_id"]
                    door_name = update["data"]["door_name"]
                    _LOGGER.info(
                        "Hardware Doorbell Press %s door id %s",
                        door_name,
                        door_id,
                    )
                    if door_id in self.doors:
                        existing_door = self.doors[door_id]
                        if existing_door is not None:
                            existing_door.doorbell_request_id = update["data"][
                                "request_id"
                            ]
                            event = "doorbell_press"
                            event_attributes = {
                                "door_name": existing_door.name,
                                "door_id": existing_door.id,
                                "type": DOORBELL_START_EVENT,
                            }

                            # We don't seem to get a message that indicates the end of the doorbell being active
                            # We just toggle the sensor for 2 seconds and return it to its original state
                            def on_complete(_fut):
                                existing_door.doorbell_request_id = None
                                event = "doorbell_press"
                                event_attributes = {
                                    "door_name": existing_door.name,
                                    "door_id": existing_door.id,
                                    "type": DOORBELL_STOP_EVENT,
                                }
                                asyncio.sleep(2)
                                existing_door.trigger_event(event, event_attributes)

                            event_done_callback = on_complete
                            _LOGGER.info(
                                "Hardware doorbell press on %s request id %s",
                                door_name,
                                update["data"]["request_id"],
                            )
                            changed_doors.append(existing_door)
                case "access.data.setting.update":
                    self.evacuation = update["data"]["evacuation"]
                    self.lockdown = update["data"]["lockdown"]
                    asyncio.run_coroutine_threadsafe(self.publish_updates(), self.loop)
                    _LOGGER.info(
                        "Settings updated. Evacuation %s, Lockdown %s",
                        self.evacuation,
                        self.lockdown,
                    )
                case _:
                    _LOGGER.debug("unhandled websocket message %s", update["event"])

            if changed_doors:
                for existing_door in changed_doors:
                    asyncio.run_coroutine_threadsafe(
                        existing_door.publish_updates(), self.loop
                    )
                    # Doing this relies on the idea that a single message will only have one message_type
                    # and that a given message will only update events if a single door was updated.
                    # Refactor would be required if that doesn't hold true.
                    if event is not None and event_attributes is not None:
                        task = asyncio.run_coroutine_threadsafe(
                            existing_door.trigger_event(event, event_attributes),
                            self.loop,
                        )
                        if event_done_callback is not None:
                            task.add_done_callback(event_done_callback)

    def on_error(self, ws: websocket.WebSocketApp, error):
        """Handle errors in the websocket client."""
        _LOGGER.exception("Got websocket error %s", error)

    def on_open(self, ws: websocket.WebSocketApp):
        """Show message on connection."""
        _LOGGER.info("Websocket connection established")

    def on_close(self, ws: websocket.WebSocketApp, close_status_code, close_msg):
        """Handle websocket closures."""
        _LOGGER.error(
            "Websocket connection closed code: %s message: %s",
            close_status_code,
            close_msg,
        )
        sslopt: dict[Any, Any]
        if self.verify_ssl is False:
            sslopt = {"cert_reqs": ssl.CERT_NONE}
        ws.run_forever(sslopt=sslopt, reconnect=5)

    def start_continuous_updates(self):
        """Start listening for updates in a separate thread using websocket-client."""
        self.update_t = Thread(target=self.listen_for_updates)
        self.update_t.daemon = True
        self.update_t.start()
        _LOGGER.info("Started websocket client in a new thread")

    def listen_for_updates(self):
        """Create a websocket client and start listening for updates."""
        uri = f"{self.websocket_host}{DEVICE_NOTIFICATIONS_URL}"
        _LOGGER.info("Listening for updates on %s", uri)
        ws = websocket.WebSocketApp(
            uri,
            header=self._websocket_headers,
            on_message=self.on_message,
            on_error=self.on_error,
            on_open=self.on_open,
            on_close=self.on_close,
        )
        sslopt = None
        if self.verify_ssl is False:
            sslopt = {"cert_reqs": ssl.CERT_NONE}
        ws.run_forever(sslopt=sslopt, reconnect=5)

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when settings change."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()

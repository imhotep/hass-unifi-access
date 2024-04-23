"""Unifi Access Hub.

This module interacts with the Unifi Access API server.
"""

import asyncio
import json
import logging
import ssl
from threading import Thread
from urllib.parse import urlparse

from requests import request
from requests.exceptions import ConnectionError as ConnError, SSLError
import urllib3
import websocket

from .const import (
    ACCESS_EVENT,
    DEVICE_NOTIFICATIONS_URL,
    DOOR_UNLOCK_URL,
    DOORBELL_START_EVENT,
    DOORBELL_STOP_EVENT,
    DOORS_URL,
    UNIFI_ACCESS_API_PORT,
)
from .door import UnifiAccessDoor
from .errors import ApiAuthError, ApiError

_LOGGER = logging.getLogger(__name__)


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
        self.update_t = None
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
        _LOGGER.info(
            "Getting door updates from Unifi Access %s Use Polling %s",
            self.host,
            self.use_polling,
        )
        data = self._make_http_request(f"{self.host}{DOORS_URL}")

        for _i, door in enumerate(data):
            door_id = door["id"]
            if door_id in self.doors:
                existing_door = self.doors[door_id]
                existing_door.name = door["name"]
                existing_door.door_position_status = door["door_position_status"]
                existing_door.door_lock_relay_status = door["door_lock_relay_status"]
            elif door["is_bind_hub"] is True:
                self._doors[door_id] = UnifiAccessDoor(
                    door_id=door["id"],
                    name=door["name"],
                    door_position_status=door["door_position_status"],
                    door_lock_relay_status=door["door_lock_relay_status"],
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
        _LOGGER.info("Got door update %s", updated_door)
        if door_id in self.doors:
            existing_door: UnifiAccessDoor = self.doors[door_id]
            existing_door.door_lock_relay_status = updated_door[
                "door_lock_relay_status"
            ]
            existing_door.door_position_status = updated_door["door_position_status"]
            existing_door.name = updated_door["name"]
            _LOGGER.info("Door %s updated", door_id)

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

    def unlock_door(self, door_id: str) -> None:
        """Test if we can authenticate with the host."""
        _LOGGER.info("Unlocking door with id %s", door_id)
        self._make_http_request(
            f"{self.host}{DOOR_UNLOCK_URL}".format(door_id=door_id), "PUT"
        )

    def _make_http_request(self, url, method="GET") -> dict:
        """Make HTTP request to Unifi Access API server."""
        r = request(
            method,
            url,
            headers=self._http_headers,
            verify=self.verify_ssl,
            timeout=10,
        )

        if r.status_code == 401:
            raise ApiAuthError

        if r.status_code != 200:
            raise ApiError

        response = r.json()

        return response["data"]

    def on_message(self, ws: websocket.WebSocketApp, message):
        """Handle messages received on the websocket client.

        Doorbell presses are relying on door names so if those are not unique, it may cause some issues
        """
        event = None
        event_attributes = None
        update = json.loads(message)
        if update != "Hello":
            _LOGGER.debug(f"Received message {message}")
            existing_door = None
            match update["event"]:
                case "access.dps_change":
                    door_id = update["data"]["door_id"]
                    _LOGGER.info("DPS Change %s", door_id)
                    if door_id in self.doors:
                        existing_door = self.doors[door_id]
                        existing_door.door_position_status = update["data"]["status"]
                        _LOGGER.info(
                            "DPS Change for existing door %s with ID %s status: %s",
                            existing_door.name,
                            door_id,
                            update["data"]["status"],
                        )
                case "access.data.device.remote_unlock":
                    door_id = update["data"]["unique_id"]
                    _LOGGER.info("Remote Unlock %s", door_id)
                    if door_id in self.doors:
                        existing_door = self.doors[door_id]
                        existing_door.door_lock_relay_status = "unlock"
                        _LOGGER.info(
                            "Remote Unlock of door %s with ID %s updated",
                            existing_door.name,
                            door_id,
                        )
                case "access.data.device.update":
                    device_type = update["data"]["device_type"]
                    if device_type == "UAH":
                        door_id = update["data"]["door"]["unique_id"]
                        _LOGGER.info("Device Update via websocket %s", door_id)
                        if door_id in self.doors:
                            existing_door = self.doors[door_id]
                            self.update_door(door_id)
                            _LOGGER.info(
                                "Door name %s with ID %s updated",
                                existing_door.name,
                                door_id,
                            )
                    elif device_type == "UAH-Ent":
                        for door_object in update["data"]["extensions"]:
                            door_id = door_object["target_value"]
                            _LOGGER.info("Device Update via websocket %s", door_id)
                            if door_id in self.doors:
                                existing_door = self.doors[door_id]
                                self.update_door(door_id)
                                _LOGGER.info(
                                    "Door name %s with ID %s updated",
                                    existing_door.name,
                                    door_id,
                                )
                                asyncio.run_coroutine_threadsafe(
                                    existing_door.publish_updates(), self.loop
                                )
                case "access.remote_view":
                    door_name = update["data"]["door_name"]
                    _LOGGER.info("Doorbell Press %s", door_name)
                    existing_door = next(
                        (
                            door
                            for door in self.doors.values()
                            if door.name == door_name
                        ),
                        None,
                    )
                    if existing_door is not None:
                        existing_door.doorbell_request_id = update["data"]["request_id"]
                        event = "doorbell_press"
                        event_attributes = {
                            "door_name": existing_door.name,
                            "door_id": existing_door.id,
                            "type": DOORBELL_START_EVENT,
                        }
                        _LOGGER.info(
                            "Doorbell press on %s Request ID %s",
                            door_name,
                            update["data"]["request_id"],
                        )
                case "access.remote_view.change":
                    doorbell_request_id = update["data"]["remote_call_request_id"]
                    _LOGGER.info(
                        "Doorbell press stopped. Request ID %s", doorbell_request_id
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
                            "Doorbell press stopped on %s Request ID %s",
                            existing_door.name,
                            doorbell_request_id,
                        )
                case "access.logs.add":
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
                        _LOGGER.info("Access log added via websocket %s", door_id)
                        if door_id in self.doors:
                            existing_door = self.doors[door_id]
                            actor = update["data"]["_source"]["actor"]["display_name"]
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
                                    "type": ACCESS_EVENT.format(type=access_type),
                                }
                                _LOGGER.info(
                                    "Door name %s with ID %s accessed by %s. Access type: %s",
                                    existing_door.name,
                                    door_id,
                                    actor,
                                    access_type,
                                )
            if existing_door is not None:
                asyncio.run_coroutine_threadsafe(
                    existing_door.publish_updates(), self.loop
                )
                if event is not None and event_attributes is not None:
                    asyncio.run_coroutine_threadsafe(
                        existing_door.trigger_event(event, event_attributes), self.loop
                    )

    def on_error(self, ws: websocket.WebSocketApp, error):
        """Handle errors in the websocket client."""
        _LOGGER.exception("Got error %s", error)

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
        sslopt = None
        if self.verify_ssl is False:
            sslopt = {"cert_reqs": ssl.CERT_NONE}
        ws.run_forever(sslopt=sslopt, reconnect=5)

    def start_continuous_updates(self):
        """Start listening for updates in a separate thread using websocket-client."""
        self.update_t = Thread(target=self.listen_for_updates)
        self.update_t.daemon = True
        self.update_t.start()

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

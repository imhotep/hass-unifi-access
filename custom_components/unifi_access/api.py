from .const import DOORS_URL, DOOR_UNLOCK_URL, UNIFI_ACCESS_API_PORT

from requests import request
from requests.exceptions import SSLError
from requests.exceptions import ConnectionError as ConnError
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from datetime import timedelta
import urllib3

from urllib.parse import urlparse

_LOGGER = logging.getLogger(__name__)


class ApiAuthError(Exception):
    "Raised when we can't authenticate with the API Token"


class ApiError(Exception):
    "Raised when we have some trouble using the API"


class UnifiAccessApi:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str, verify_ssl: bool = False) -> None:
        """Initialize."""
        self.verify_ssl = verify_ssl
        if self.verify_ssl == False:
            _LOGGER.warning(f"SSL Verification disabled for {host}")
            urllib3.disable_warnings()

        host_parts = host.split(":")
        parsed_host = urlparse(host)

        hostname = parsed_host.hostname if parsed_host.hostname else host_parts[0]
        port = (
            parsed_host.port
            if parsed_host.port
            else (host_parts[1] if len(host_parts) > 1 else UNIFI_ACCESS_API_PORT)
        )
        self.host = f"https://{hostname}:{port}"
        self._api_token = None
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def set_api_token(self, api_token):
        self._api_token = api_token
        self._headers["Authorization"] = f"Bearer {self._api_token}"

    def update(self):
        # _LOGGER.info(f"Getting door updates from Unifi Access {self.host}")
        data = self._make_http_request(f"{self.host}{DOORS_URL}")

        doors: list[UnifiAccessDoor] = []

        for i, door in enumerate(data):
            if door["is_bind_hub"] == True:
                doors.append(
                    UnifiAccessDoor(
                        door_id=door["id"],
                        name=door["name"],
                        door_position_status=door["door_position_status"],
                        door_lock_relay_status=door["door_lock_relay_status"],
                        api=self,
                    )
                )

        return doors

    def update_door(self, door_id: int) -> None:
        _LOGGER.info(f"Getting door update from Unifi Access with id {door_id}")
        self._make_http_request(f"{self.host}{DOORS_URL}/{door_id}")

    def authenticate(self, api_token: str) -> str:
        """Test if we can authenticate with the host."""
        self.set_api_token(api_token)
        _LOGGER.info(f"Authenticating {self.host}")
        try:
            self.update()
        except ApiError:
            _LOGGER.error(
                f"Could perform action with {self.host}. Check host and token."
            )
            return "api_error"
        except ApiAuthError:
            _LOGGER.error(
                f"Could not authenticate with {self.host}. Check host and token."
            )
            return "api_auth_error"
        except SSLError:
            _LOGGER.error(f"Error validating SSL Certificate for {self.host}.")
            return "ssl_error"
        except ConnError:
            _LOGGER.error(f"Cannot connect to {self.host}.")
            return "cannot_connect"

        return "ok"

    def unlock_door(self, door_id: str) -> None:
        """Test if we can authenticate with the host."""
        _LOGGER.info(f"Unlocking door with id {door_id}")
        self._make_http_request(
            f"{self.host}{DOOR_UNLOCK_URL}".format(door_id=door_id), "PUT"
        )

    def _make_http_request(self, url, method="GET") -> None:
        r = request(
            method,
            url,
            headers=self._headers,
            verify=self.verify_ssl,
            timeout=10,
        )

        if r.status_code == 401:
            raise ApiAuthError

        if r.status_code != 200:
            raise ApiError

        response = r.json()

        return response["data"]


class UnifiAccessCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Unifi Access Coordinator",
            update_interval=timedelta(seconds=3),
        )
        self.api = api

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(10):
                return await self.hass.async_add_executor_job(self.api.update)
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")


class UnifiAccessDoor:
    def __init__(
        self,
        door_id: str,
        name: str,
        door_position_status: str,
        door_lock_relay_status: str,
        api: UnifiAccessApi,
    ) -> None:
        self._is_locking = False
        self._is_unlocking = False
        self._api = api
        self._id = door_id
        self.name = name
        self.door_position_status = door_position_status
        self.door_lock_relay_status = door_lock_relay_status

    @property
    def id(self) -> str:
        return self._id

    @property
    def is_open(self):
        return self.door_position_status == "open"

    @property
    def is_locked(self):
        """Solely used for locked state when calling lock"""
        return self.door_lock_relay_status == "lock"

    @property
    def is_locking(self):
        """Solely used for locking state when calling lock"""
        return False

    @property
    def is_unlocking(self):
        """Solely used for unlocking state when calling unlock"""
        return self._is_unlocking

    def unlock(self) -> None:
        if self.is_locked:
            self._is_unlocking = True
            self._api.unlock_door(self._id)
            self._is_unlocking = False
            _LOGGER.info(f"Door with door ID {self.id} is unlocked")
        else:
            _LOGGER.error(f"Door with door ID {self.id} is already unlocked")

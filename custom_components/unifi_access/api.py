from .const import DOORS_URL, DOOR_LOCK_URL, DOOR_UNLOCK_URL, UNIFI_ACCESS_API_PORT

from requests import request
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

urllib3.disable_warnings()

_LOGGER = logging.getLogger(__name__)


class ApiAuthError(Exception):
    "Raised when we can't authenticate with the API Token"


class ApiError(Exception):
    "Raised when we have some trouble using the API"


class UnifiAccessApi:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = f"https://{host}:{UNIFI_ACCESS_API_PORT}"
        self._api_token = None
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def set_api_token(self, api_token):
        self._api_token = api_token
        self._headers["Authorization"] = f"Bearer {self._api_token}"

    def update(self):
        _LOGGER.info(f"Getting door updates from Unifi Access {self.host}")

        data = self._make_http_request(f"{self.host}{DOORS_URL}")

        doors: list[UnifiAccessDoor] = []

        for i, door in enumerate(data):
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

    def authenticate(self, api_token: str) -> bool:
        """Test if we can authenticate with the host."""
        self.set_api_token(api_token)
        _LOGGER.info(f"Authenticating {self.host}")
        try:
            self.update()
        except ApiError:
            _LOGGER.error(f"Error authenticating {self.host}")
            return False
        return True

    def lock_door(self, door_id: str) -> None:
        """Test if we can authenticate with the host."""
        _LOGGER.info(f"Locking door with id {door_id}")
        self._make_http_request(
            f"{self.host}{DOOR_LOCK_URL}".format(door_id=door_id), "PUT"
        )

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
            verify=False,
            timeout=10,
        )

        if r.status_code != 200:
            _LOGGER.error(
                f"Could not authenticate with {self.host}. Check host and token. URL: {url}"
            )
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
        self._api = api
        self._id = door_id
        self.name = name
        self.door_position_status = door_position_status
        self.door_lock_relay_status = door_lock_relay_status

    @property
    def id(self) -> str:
        return self._id

    def unlock(self) -> None:
        self._api.unlock_door(self._id)

    def lock(self) -> None:
        self._api.lock_door(self._id)

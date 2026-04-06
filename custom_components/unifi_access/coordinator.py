"""Unifi Access Coordinator."""

import asyncio
from collections.abc import Callable, Coroutine
from datetime import timedelta
import logging
from typing import Any, TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from unifi_access_api import ApiAuthError, ApiError

from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


class UnifiAccessCoordinator(DataUpdateCoordinator[_T]):
    """Parameterised coordinator for both door and emergency data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        hub: UnifiAccessHub,
        *,
        name: str,
        update_method: Callable[[], Coroutine[Any, Any, _T]],
        always_update: bool = False,
    ) -> None:
        """Initialize Unifi Access Coordinator."""
        self.hub = hub
        self._update_method = update_method
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            config_entry=config_entry,
            always_update=always_update,
            update_interval=timedelta(seconds=3) if hub.use_polling else None,
        )

    async def _async_update_data(self) -> _T:
        """Fetch data from the API."""
        try:
            async with asyncio.timeout(10):
                return await self._update_method()
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed("Error communicating with API") from err

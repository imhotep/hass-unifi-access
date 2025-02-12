"""Unifi Access Coordinator.

This module has the Unifi Access Coordinator to be used by entities.
"""

import asyncio
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .errors import ApiAuthError, ApiError

_LOGGER = logging.getLogger(__name__)


class UnifiAccessCoordinator(DataUpdateCoordinator):
    """Unifi Access Coordinator. This is mostly used for local polling."""

    def __init__(self, hass: HomeAssistant, hub) -> None:
        """Initialize Unifi Access Coordinator."""
        update_interval = timedelta(seconds=3) if hub.use_polling is True else None

        super().__init__(
            hass,
            _LOGGER,
            name="Unifi Access Coordinator",
            always_update=True,
            update_interval=update_interval,
        )
        self.hub = hub

    async def _async_update_data(self):
        """Handle Unifi Access Coordinator updates."""
        try:
            async with asyncio.timeout(10):
                return await self.hass.async_add_executor_job(self.hub.update)
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed("Error communicating with API") from err


class UnifiAccessEvacuationAndLockdownSwitchCoordinator(DataUpdateCoordinator):
    """Unifi Access Switch Coordinator."""

    def __init__(self, hass: HomeAssistant, hub) -> None:
        """Initialize Unifi Access Switch Coordinator."""
        update_interval = timedelta(seconds=3) if hub.use_polling is True else None

        super().__init__(
            hass,
            _LOGGER,
            name="Unifi Access Evacuation and Lockdown Switch Coordinator",
            update_interval=update_interval,
        )
        self.hub = hub

    async def _async_update_data(self):
        """Handle Unifi Access Switch Coordinator updates."""
        try:
            async with asyncio.timeout(10):
                return await self.hass.async_add_executor_job(
                    self.hub.get_doors_emergency_status
                )
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed("Error communicating with API") from err

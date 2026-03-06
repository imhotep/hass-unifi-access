"""Unifi Access Coordinator."""

import asyncio
import logging
from datetime import timedelta

from unifi_access_api import ApiAuthError, ApiError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)


class UnifiAccessCoordinator(DataUpdateCoordinator):
    """Unifi Access Coordinator. Used for local polling and WS push."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        hub: UnifiAccessHub,
    ) -> None:
        """Initialize Unifi Access Coordinator."""
        self.hub = hub
        super().__init__(
            hass,
            _LOGGER,
            name="Unifi Access Coordinator",
            config_entry=config_entry,
            always_update=True,
            update_interval=timedelta(seconds=3) if hub.use_polling else None,
        )

    async def _async_update_data(self):
        """Fetch door data from the API."""
        try:
            async with asyncio.timeout(10):
                return await self.hub.async_update()
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed("Error communicating with API") from err


class UnifiAccessEmergencyCoordinator(DataUpdateCoordinator):
    """Unifi Access Emergency (evacuation/lockdown) Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        hub: UnifiAccessHub,
    ) -> None:
        """Initialize Unifi Access Emergency Coordinator."""
        self.hub = hub
        super().__init__(
            hass,
            _LOGGER,
            name="Unifi Access Emergency Coordinator",
            config_entry=config_entry,
            update_interval=timedelta(seconds=3) if hub.use_polling else None,
        )

    async def _async_update_data(self):
        """Fetch emergency status from the API."""
        try:
            async with asyncio.timeout(10):
                return await self.hub.async_get_emergency_status()
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed("Error communicating with API") from err

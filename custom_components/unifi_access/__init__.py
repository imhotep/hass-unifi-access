"""The Unifi Access integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .api import UnifiAccessApi

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
# PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.LOCK]
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.LOCK]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Unifi Access from a config entry."""
    api = UnifiAccessApi(entry.data["host"], entry.data["verify_ssl"])
    api.set_api_token(entry.data["api_token"])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

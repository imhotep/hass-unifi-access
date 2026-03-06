"""The Unifi Access integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from unifi_access_api import UnifiAccessApiClient

from .coordinator import UnifiAccessCoordinator, UnifiAccessEmergencyCoordinator
from .hub import UnifiAccessHub

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


@dataclass
class UnifiAccessData:
    """Runtime data for the Unifi Access integration."""

    hub: UnifiAccessHub
    coordinator: UnifiAccessCoordinator
    emergency_coordinator: UnifiAccessEmergencyCoordinator


type UnifiAccessConfigEntry = ConfigEntry[UnifiAccessData]


async def async_setup_entry(
    hass: HomeAssistant, entry: UnifiAccessConfigEntry
) -> bool:
    """Set up Unifi Access from a config entry."""
    session = async_get_clientsession(hass, verify_ssl=entry.data["verify_ssl"])

    client = UnifiAccessApiClient(
        host=entry.data["host"],
        api_token=entry.data["api_token"],
        session=session,
        verify_ssl=entry.data["verify_ssl"],
    )

    hub = UnifiAccessHub(client, use_polling=entry.data["use_polling"])

    coordinator = UnifiAccessCoordinator(hass, entry, hub)
    await coordinator.async_config_entry_first_refresh()

    emergency_coordinator = UnifiAccessEmergencyCoordinator(hass, entry, hub)
    await emergency_coordinator.async_config_entry_first_refresh()

    # Wire WebSocket push → coordinator updates
    hub.on_doors_updated = lambda: coordinator.async_set_updated_data(hub.doors)
    hub.on_emergency_updated = (
        lambda: emergency_coordinator.async_set_updated_data(True)
    )

    entry.runtime_data = UnifiAccessData(
        hub=hub,
        coordinator=coordinator,
        emergency_coordinator=emergency_coordinator,
    )

    hub.create_task = lambda coro: entry.async_create_background_task(
        hass, coro, "unifi_access_background_task"
    )

    if not hub.use_polling:
        hub.start_websocket()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: UnifiAccessConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.hub.async_close()

    return unload_ok

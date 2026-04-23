"""The Unifi Access integration."""

from __future__ import annotations

from dataclasses import dataclass
import ssl

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import ssl as ssl_util
from unifi_access_api import ApiConnectionError, EmergencyStatus, UnifiAccessApiClient

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION
from .coordinator import UnifiAccessCoordinator
from .hub import DoorState, UnifiAccessHub

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.COVER,
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
    coordinator: UnifiAccessCoordinator[dict[str, DoorState]]
    emergency_coordinator: UnifiAccessCoordinator[EmergencyStatus]
    store: Store


type UnifiAccessConfigEntry = ConfigEntry[UnifiAccessData]


async def async_setup_entry(hass: HomeAssistant, entry: UnifiAccessConfigEntry) -> bool:
    """Set up Unifi Access from a config entry."""
    session = async_get_clientsession(hass, verify_ssl=entry.data["verify_ssl"])

    ssl_context: ssl.SSLContext | bool = False
    if entry.data["verify_ssl"]:
        # SSL context creation may call into blocking cert-loading functions.
        ssl_context = await hass.async_add_executor_job(ssl_util.client_context)

    client_kwargs = {
        "host": entry.data["host"],
        "api_token": entry.data["api_token"],
        "session": session,
        "verify_ssl": entry.data["verify_ssl"],
        "ssl_context": ssl_context,
    }

    client = UnifiAccessApiClient(**client_kwargs)

    hub = UnifiAccessHub(client, use_polling=entry.data["use_polling"])

    try:
        await hub.client.authenticate()
    except ApiConnectionError as err:
        raise ConfigEntryNotReady("Unable to connect to UniFi Access") from err

    coordinator: UnifiAccessCoordinator[dict[str, DoorState]] = UnifiAccessCoordinator(
        hass,
        entry,
        hub,
        name="Unifi Access Coordinator",
        update_method=hub.async_update,
        always_update=True,
    )
    await coordinator.async_config_entry_first_refresh()

    # Restore persisted entity types (e.g. garage/gate for UGT doors)
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored_data = await store.async_load() or {}
    # Migrate old format: {"entity_types": {"door_id": "value"}}
    if "entity_types" in stored_data:
        stored_data = stored_data["entity_types"]
    for door_id, door_state in coordinator.data.items():
        if door_id in stored_data:
            door_state.entity_type = stored_data[door_id]

    emergency_coordinator: UnifiAccessCoordinator[EmergencyStatus] = (
        UnifiAccessCoordinator(
            hass,
            entry,
            hub,
            name="Unifi Access Emergency Coordinator",
            update_method=hub.async_get_emergency_status,
        )
    )
    await emergency_coordinator.async_config_entry_first_refresh()

    # Wire WebSocket push → coordinator updates
    hub.on_doors_updated = lambda: coordinator.async_set_updated_data(hub.doors)
    hub.on_emergency_updated = lambda: emergency_coordinator.async_set_updated_data(
        EmergencyStatus(evacuation=hub.evacuation, lockdown=hub.lockdown)
    )

    entry.runtime_data = UnifiAccessData(
        hub=hub,
        coordinator=coordinator,
        emergency_coordinator=emergency_coordinator,
        store=store,
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


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of devices that are no longer present."""
    hub = config_entry.runtime_data.hub
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN and identifier[1] in hub.doors
    )

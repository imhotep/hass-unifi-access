"""The Unifi Access integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.entity_registry as er

from .const import DOMAIN
from .coordinator import UnifiAccessCoordinator
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
_LOGGER = logging.getLogger(__name__)


async def remove_stale_entities(hass: HomeAssistant, entry_id: str):
    """Remove entities that are stale."""
    _LOGGER.debug("Removing stale entities")
    registry = er.async_get(hass)
    config_entry_entities = registry.entities.get_entries_for_config_entry_id(entry_id)
    stale_entities = [
        entity
        for entity in config_entry_entities
        if (entity.disabled or not hass.states.get(entity.entity_id))
    ]
    for entity in stale_entities:
        _LOGGER.debug("Removing stale entity: %s", entity.entity_id)
        registry.async_remove(entity.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Unifi Access from a config entry."""
    hub = UnifiAccessHub(
        entry.data["host"], entry.data["verify_ssl"], entry.data["use_polling"]
    )
    hub.set_api_token(entry.data["api_token"])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub

    coordinator: UnifiAccessCoordinator = UnifiAccessCoordinator(hass, hub)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN]["coordinator"] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await remove_stale_entities(hass, entry.entry_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

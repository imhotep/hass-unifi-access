"""The Unifi Access integration."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
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

# Service schemas
SERVICE_ENABLE_USER = "enable_user"
SERVICE_DISABLE_USER = "disable_user"
SERVICE_UPDATE_USER_PIN = "update_user_pin"

USER_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("user_id"): cv.string,
    }
)

UPDATE_PIN_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("user_id"): cv.string,
        vol.Optional("pin"): cv.string,
    }
)


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


async def async_enable_user_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle enable user service call."""
    config_entry_id = call.data["config_entry_id"]
    user_id = call.data["user_id"]
    
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry_id]
    
    await hass.async_add_executor_job(hub.update_user_status, user_id, True)
    _LOGGER.info("User %s enabled via service call", user_id)


async def async_disable_user_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle disable user service call."""
    config_entry_id = call.data["config_entry_id"]
    user_id = call.data["user_id"]
    
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry_id]
    
    await hass.async_add_executor_job(hub.update_user_status, user_id, False)
    _LOGGER.info("User %s disabled via service call", user_id)


async def async_update_user_pin_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle update user PIN service call."""
    config_entry_id = call.data["config_entry_id"]
    user_id = call.data["user_id"]
    pin = call.data.get("pin")
    
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry_id]
    
    await hass.async_add_executor_job(hub.update_user_pin, user_id, pin)
    _LOGGER.info("User %s PIN updated via service call", user_id)


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

    # Register services if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_ENABLE_USER):
        hass.services.async_register(
            DOMAIN, SERVICE_ENABLE_USER, async_enable_user_service, USER_SERVICE_SCHEMA
        )
        
    if not hass.services.has_service(DOMAIN, SERVICE_DISABLE_USER):
        hass.services.async_register(
            DOMAIN, SERVICE_DISABLE_USER, async_disable_user_service, USER_SERVICE_SCHEMA
        )
        
    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_USER_PIN):
        hass.services.async_register(
            DOMAIN, SERVICE_UPDATE_USER_PIN, async_update_user_pin_service, UPDATE_PIN_SERVICE_SCHEMA
        )

    await remove_stale_entities(hass, entry.entry_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove services if this is the last config entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_ENABLE_USER)
            hass.services.async_remove(DOMAIN, SERVICE_DISABLE_USER)
            hass.services.async_remove(DOMAIN, SERVICE_UPDATE_USER_PIN)

    return unload_ok

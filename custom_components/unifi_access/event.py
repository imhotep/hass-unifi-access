"""Platform for sensor integration."""

from __future__ import annotations

import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACCESS_ENTRY_EVENT,
    ACCESS_EXIT_EVENT,
    DOMAIN,
    DOORBELL_START_EVENT,
    DOORBELL_STOP_EVENT,
)
from .door import UnifiAccessDoor
from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add event entity for passed config entry."""
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]

    if hub.use_polling is False:
        coordinator = hass.data[DOMAIN]["coordinator"]

        async_add_entities(
            (AccessEventEntity(hass, door) for door in coordinator.data.values()),
        )
        async_add_entities(
            (
                DoorbellPressedEventEntity(hass, door)
                for door in coordinator.data.values()
            ),
        )


class AccessEventEntity(EventEntity):
    """Authorized User Event Entity."""

    _attr_event_types = [ACCESS_ENTRY_EVENT, ACCESS_EXIT_EVENT]
    _attr_translation_key = "access_event"
    _attr_has_entity_name = True
    should_poll = False

    def __init__(self, hass: HomeAssistant, door) -> None:
        """Initialize Unifi Access Door Lock."""
        self.hass = hass
        self.door: UnifiAccessDoor = door
        self._attr_unique_id = f"{self.door.id}_access"
        self._attr_translation_placeholders = {"door_name": self.door.name}

    @property
    def device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model="UAH",
            manufacturer="Unifi",
        )

    def _async_handle_event(self, event: str, event_attributes: dict[str, str]) -> None:
        """Handle access events."""
        _LOGGER.info("Triggering event %s with attributes %s", event, event_attributes)
        self._trigger_event(event, event_attributes)
        self.async_write_ha_state()
        self.hass.bus.fire(event, event_attributes)

    async def async_added_to_hass(self) -> None:
        """Register event listener with hub."""
        self.door.add_event_listener("access", self._async_handle_event)

    async def async_will_remove_from_hass(self) -> None:
        """Handle updates in case of push and removal."""
        await super().async_will_remove_from_hass()
        self.door.remove_event_listener("access", self._async_handle_event)


class DoorbellPressedEventEntity(EventEntity):
    """Doorbell Press Event Entity."""

    _attr_device_class = EventDeviceClass.DOORBELL
    _attr_event_types = [DOORBELL_START_EVENT, DOORBELL_STOP_EVENT]
    _attr_translation_key = "doorbell_event"
    _attr_has_entity_name = True
    should_poll = False

    def __init__(self, hass: HomeAssistant, door) -> None:
        """Initialize Unifi Access Doorbell Event."""
        self.hass = hass
        self.door: UnifiAccessDoor = door
        self._attr_unique_id = f"{self.door.id}_doorbell_press"
        self._attr_translation_placeholders = {"door_name": self.door.name}

    @property
    def device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    def _async_handle_event(self, event: str, event_attributes: dict[str, str]) -> None:
        """Handle doorbell events."""
        _LOGGER.info("Received event %s with attributes %s", event, event_attributes)
        self._trigger_event(event, event_attributes)
        self.async_write_ha_state()
        self.hass.bus.fire(event, event_attributes)

    async def async_added_to_hass(self) -> None:
        """Register event listener with door."""
        self.door.add_event_listener("doorbell_press", self._async_handle_event)

    async def async_will_remove_from_hass(self) -> None:
        """Handle updates in case of push and removal."""
        await super().async_will_remove_from_hass()
        self.door.remove_event_listener("doorbell_press", self._async_handle_event)

"""Platform for sensor integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add binary_sensor entity for passed config entry."""
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = hass.data[DOMAIN]["coordinator"]

    binary_sensor_entities: list[UnifiDoorStatusEntity | UnifiDoorbellStatusEntity] = []
    for key in coordinator.data:
        binary_sensor_entities.append(UnifiDoorStatusEntity(coordinator, key))
        if hub.use_polling is False:
            binary_sensor_entities.append(UnifiDoorbellStatusEntity(coordinator, key))
    async_add_entities(binary_sensor_entities)


class UnifiDoorStatusEntity(CoordinatorEntity, BinarySensorEntity):
    """Unifi Access DPS Entity."""

    should_poll = False
    _attr_translation_key = "access_door_dps"
    _attr_has_entity_name = True

    def __init__(self, coordinator, door_id) -> None:
        """Initialize DPS Entity."""
        super().__init__(coordinator, context=door_id)
        self._attr_device_class = BinarySensorDeviceClass.DOOR
        self.door = self.coordinator.data[door_id]
        self._attr_unique_id = self.door.id
        self.device_name = self.door.name
        self._attr_available = self.door.door_position_status is not None
        self._attr_is_on = self.door.door_position_status == "open"

    @property
    def device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    @property
    def is_on(self) -> bool:
        """Get door status."""
        return self.door.is_open

    def _handle_coordinator_update(self) -> None:
        """Handle updates in case of polling."""
        self._attr_is_on = self.door.is_open
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle updates in case of push."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Handle updates in case of push and removal."""
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)


class UnifiDoorbellStatusEntity(CoordinatorEntity, BinarySensorEntity):
    """Unifi Access Doorbell Entity."""

    should_poll = False

    def __init__(self, coordinator, door_id) -> None:
        """Initialize Doorbell Entity."""
        super().__init__(coordinator, context=door_id)
        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self.door = self.coordinator.data[door_id]
        self._attr_unique_id = f"doorbell_{self.door.id}"
        self.device_name = self.door.name
        self._attr_name = f"{self.door.name} Doorbell"
        self._attr_available = self.door.doorbell_pressed is not None
        self._attr_is_on = self.door.doorbell_pressed

    @property
    def device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model="UAH",
            manufacturer="Unifi",
        )

    @property
    def is_on(self) -> bool:
        """Get doorbell status."""
        return self.door.doorbell_pressed

    def _handle_coordinator_update(self) -> None:
        """Handle updates in case of polling."""
        self._attr_is_on = self.door.doorbell_pressed
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle updates in case of push."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Handle updates in case of push and removal."""
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)

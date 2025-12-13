"""Platform for cover integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .door import UnifiAccessDoor, DoorEntityType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add cover entity for passed config entry."""

    coordinator = hass.data[DOMAIN]["coordinator"]

    # Only create cover entities for doors configured as garage or gate
    async_add_entities(
        UnifiGarageDoorCoverEntity(coordinator, key)
        for key in coordinator.data
        if coordinator.data[key].entity_type in (DoorEntityType.GARAGE, DoorEntityType.GATE)
    )


class UnifiGarageDoorCoverEntity(CoordinatorEntity, CoverEntity):
    """Unifi Access Garage/Gate Door Cover."""

    _attr_translation_key = "access_cover"
    _attr_has_entity_name = True
    _attr_name = None

    @property
    def device_class(self) -> CoverDeviceClass:
        """Return the device class based on entity_type."""
        if self.door.entity_type == DoorEntityType.GATE:
            return CoverDeviceClass.GATE
        return CoverDeviceClass.GARAGE

    def __init__(self, coordinator, door_id) -> None:
        """Initialize Unifi Access Garage Door Cover."""
        super().__init__(coordinator, context=door_id)
        self.door: UnifiAccessDoor = self.coordinator.data[door_id]
        self._attr_unique_id = f"{self.door.id}_cover"
        self._attr_translation_placeholders = {"door_name": self.door.name}
        self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        self._attr_should_poll = False

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Garage Door Cover device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Garage Door Cover to Home Assistant."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Garage Door Cover from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover (trigger the door motor)."""
        await self.hass.async_add_executor_job(self.door.unlock)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover (trigger the door motor)."""
        # Garage doors use the same unlock signal for both open and close
        # It's a momentary trigger that activates the motor
        await self.hass.async_add_executor_job(self.door.unlock)

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed (door is closed and locked)."""
        # Door is considered "closed" if position is closed and locked
        return not self.door.is_open and self.door.is_locked

    @property
    def is_opening(self) -> bool | None:
        """Return if the cover is opening."""
        return self.door.is_unlocking

    @property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing."""
        return self.door.is_locking

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Garage Door Cover updates from coordinator."""
        self._attr_is_closed = not self.door.is_open and self.door.is_locked
        self._attr_is_opening = self.door.is_unlocking
        self._attr_is_closing = self.door.is_locking
        self.async_write_ha_state()

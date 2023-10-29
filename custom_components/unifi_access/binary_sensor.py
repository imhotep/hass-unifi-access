"""Platform for sensor integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging

_LOGGER = logging.getLogger(__name__)


from .const import DOMAIN
from .api import UnifiAccessApi, UnifiAccessCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Binary Sensor for passed config entry"""
    api: UnifiAccessApi = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = UnifiAccessCoordinator(hass, api)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        UnifiDoorStatusEntity(coordinator, idx)
        for idx, ent in enumerate(coordinator.data)
    )


class UnifiDoorStatusEntity(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, idx) -> None:
        super().__init__(coordinator, context=idx)
        self._attr_device_class = BinarySensorDeviceClass.DOOR
        self.idx = idx
        door = self.coordinator.data[idx]
        self._attr_unique_id = door.id
        self.device_name = door.name
        self._attr_name = f"{door.name} Door Position Sensor"
        self._attr_available = door.door_position_status != None
        self._attr_is_on = door.door_position_status == "open"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.device_name,
            model="UAH",
            manufacturer="Unifi",
        )

    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.coordinator.data[self.idx].is_open
        self.async_write_ha_state()

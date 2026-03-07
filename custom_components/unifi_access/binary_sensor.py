"""Platform for binary sensor integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry
from .const import DOMAIN
from .coordinator import UnifiAccessCoordinator
from .entity import UnifiAccessDoorEntity
from .hub import DoorState

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add binary_sensor entity for passed config entry."""
    data = config_entry.runtime_data
    coordinator = data.coordinator

    entities: list[UnifiDoorStatusEntity | UnifiDoorbellStatusEntity] = []
    for key in coordinator.data:
        entities.append(UnifiDoorStatusEntity(coordinator, key))
        if not data.hub.use_polling:
            entities.append(UnifiDoorbellStatusEntity(coordinator, key))
    async_add_entities(entities)


class UnifiDoorStatusEntity(UnifiAccessDoorEntity, BinarySensorEntity):
    """Unifi Access DPS Entity."""

    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_translation_key = "access_door_dps"

    def __init__(self, coordinator: UnifiAccessCoordinator[dict[str, DoorState]], door_id: str) -> None:
        """Initialize DPS Entity."""
        super().__init__(coordinator, coordinator.data[door_id])
        self._attr_unique_id = self.door.id

    @property
    def is_on(self) -> bool:
        """Get door status."""
        return self.door.is_open


class UnifiDoorbellStatusEntity(UnifiAccessDoorEntity, BinarySensorEntity):
    """Unifi Access Doorbell Entity."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_translation_key = "doorbell_status"

    def __init__(self, coordinator: UnifiAccessCoordinator[dict[str, DoorState]], door_id: str) -> None:
        """Initialize Doorbell Entity."""
        super().__init__(coordinator, coordinator.data[door_id])
        self._attr_unique_id = f"doorbell_{self.door.id}"

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

"""Platform for sensor integration."""

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry
from .coordinator import UnifiAccessCoordinator
from .entity import UnifiAccessDoorEntity
from .hub import DoorState

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensor entity for passed config entry."""
    data = config_entry.runtime_data

    if data.hub.supports_door_lock_rules:
        async_add_entities(
            [
                sensor_entity(data.coordinator, door_id)
                for door_id in data.coordinator.data
                for sensor_entity in (
                    TemporaryLockRuleSensorEntity,
                    TemporaryLockRuleEndTimeSensorEntity,
                )
            ]
        )


class TemporaryLockRuleSensorEntity(UnifiAccessDoorEntity, SensorEntity):
    """Unifi Access Temporary Lock Rule Sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "door_lock_rule"

    def __init__(self, coordinator: UnifiAccessCoordinator[dict[str, DoorState]], door_id: str) -> None:
        """Initialize Unifi Access Door Lock Rule Sensor."""
        super().__init__(coordinator, coordinator.data[door_id])
        self._attr_unique_id = f"door_lock_rule_sensor_{self.door.id}"

    @property
    def native_value(self) -> str:
        """Get native value."""
        return self.door.lock_rule


class TemporaryLockRuleEndTimeSensorEntity(UnifiAccessDoorEntity, SensorEntity):
    """Unifi Access Temporary Lock Rule Sensor End Time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "door_lock_rule_ended_time"

    def __init__(self, coordinator: UnifiAccessCoordinator[dict[str, DoorState]], door_id: str) -> None:
        """Initialize Unifi Access Door Lock Rule Sensor End Time."""
        super().__init__(coordinator, coordinator.data[door_id])
        self._attr_unique_id = f"door_lock_rule_sensor_ended_time_{self.door.id}"

    @property
    def native_value(self) -> datetime | None:
        """Get native value."""
        if self.door.lock_rule_ended_time and int(self.door.lock_rule_ended_time) != 0:
            return datetime.fromtimestamp(
                int(self.door.lock_rule_ended_time), tz=UTC
            )
        return None

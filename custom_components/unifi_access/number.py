"""Platform for number (interval) integration."""

from homeassistant.components.number import RestoreNumber
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry
from .const import DOMAIN
from .hub import DoorState


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add number entity for passed config entry."""
    data = config_entry.runtime_data

    if data.hub.supports_door_lock_rules:
        async_add_entities(
            [
                TemporaryLockRuleIntervalNumberEntity(door)
                for door in data.coordinator.data.values()
            ]
        )


class TemporaryLockRuleIntervalNumberEntity(RestoreNumber):
    """Unifi Access Temporary Lock Rule Interval."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "door_lock_rule_interval"

    def __init__(self, door: DoorState) -> None:
        """Initialize Unifi Access Door Lock Rule Interval."""
        super().__init__()
        self.door = door
        self._attr_unique_id = f"door_lock_rule_interval_{self.door.id}"
        self._attr_native_value = 10
        self._attr_native_min_value = 1
        self._attr_native_max_value = 480

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Door Lock device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Door Lock Rule Interval to Home Assistant."""
        await super().async_added_to_hass()
        await self.async_get_last_number_data()
        if self.native_value:
            self.door.lock_rule_interval = int(self.native_value)

    def set_native_value(self, value: float) -> None:
        """Select Door Lock Rule Interval (in minutes)."""
        self._attr_native_value = value
        self.door.lock_rule_interval = int(value)

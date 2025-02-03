"""Platform for number (interval) integration."""

import logging

from homeassistant.components.number import RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .door import UnifiAccessDoor
from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add number entity for passed config entry."""
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = hass.data[DOMAIN]["coordinator"]

    if hub.supports_door_lock_rules:
        async_add_entities(
            [
                TemporaryLockRuleIntervalNumberEntity(door)
                for door in coordinator.data.values()
            ]
        )


class TemporaryLockRuleIntervalNumberEntity(RestoreNumber):
    """Unifi Access Temporary Lock Rule Interval Interval."""

    _attr_translation_key = "door_lock_rule_interval"
    _attr_has_entity_name = True
    should_poll = False

    def __init__(self, door: UnifiAccessDoor) -> None:
        """Initialize Unifi Access Door Lock Rule Interval."""
        super().__init__()
        self.door: UnifiAccessDoor = door
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
        "Select Door Lock Rule Interval (in minutes)."
        self._attr_native_value = value
        self.door.lock_rule_interval = int(value)

"""Platform for number (interval) integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import UnifiAccessCoordinator
from .door import UnifiAccessDoor
from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Select entity for passed config entry."""
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]

    coordinator: UnifiAccessCoordinator = UnifiAccessCoordinator(hass, hub)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [TemporaryLockRuleSensorEntity(door) for door in coordinator.data.values()]
    )


class TemporaryLockRuleSensorEntity(SensorEntity):
    """Unifi Access Temporary Lock Rule Sensor."""

    def __init__(self, door: UnifiAccessDoor) -> None:
        """Initialize Unifi Access Door Lock Rule Sensor."""
        super().__init__()
        self.door: UnifiAccessDoor = door
        self._attr_unique_id = f"door_lock_rule_sensor_{self.door.id}"
        self._attr_name = f"{self.door.name} Current Door Lock Rule"
        self._attr_native_value = f"{self.door.lock_rule}"

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model="UAH",
            manufacturer="Unifi",
        )

    @property
    def native_value(self) -> str:
        """Get native value."""
        return self.door.lock_rule

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Door Lock to Home Assistant."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Door Lock from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)

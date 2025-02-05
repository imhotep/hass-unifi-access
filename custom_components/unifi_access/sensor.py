"""Platform for number (interval) integration."""

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .door import UnifiAccessDoor
from .hub import UnifiAccessHub


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensor entity for passed config entry."""
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = hass.data[DOMAIN]["coordinator"]

    if hub.supports_door_lock_rules:
        async_add_entities(
            [
                sensor_entity(door)
                for door in coordinator.data.values()
                for sensor_entity in (
                    TemporaryLockRuleSensorEntity,
                    TemporaryLockRuleEndTimeSensorEntity,
                )
            ]
        )


class TemporaryLockRuleSensorEntity(SensorEntity):
    """Unifi Access Temporary Lock Rule Sensor."""

    should_poll = False

    _attr_translation_key = "door_lock_rule"
    _attr_has_entity_name = True

    def __init__(self, door: UnifiAccessDoor) -> None:
        """Initialize Unifi Access Door Lock Rule Sensor."""
        super().__init__()
        self.door: UnifiAccessDoor = door
        self._attr_unique_id = f"door_lock_rule_sensor_{self.door.id}"
        self._attr_native_value = f"{self.door.lock_rule}"

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
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


class TemporaryLockRuleEndTimeSensorEntity(SensorEntity):
    """Unifi Access Temporary Lock Rule Sensor End Time."""

    should_poll = False

    _attr_translation_key = "door_lock_rule_ended_time"
    _attr_has_entity_name = True

    def __init__(self, door: UnifiAccessDoor) -> None:
        """Initialize Unifi Access Door Lock Rule Sensor End Time."""
        super().__init__()
        self.door: UnifiAccessDoor = door
        self._attr_unique_id = f"door_lock_rule_sensor_ended_time_{self.door.id}"
        self._attr_native_value = self._get_ended_time()

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    def _get_ended_time(self):
        if self.door.lock_rule_ended_time and int(self.door.lock_rule_ended_time) != 0:
            utc_timestamp = int(self.door.lock_rule_ended_time)
            utc_datetime = datetime.fromtimestamp(utc_timestamp, tz=UTC)
            local_datetime = utc_datetime.astimezone()
            return f" {local_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        return ""

    @property
    def native_value(self) -> str:
        """Get native value."""
        return self._get_ended_time()

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Door Lock to Home Assistant."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Door Lock from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)

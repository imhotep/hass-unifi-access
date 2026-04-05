"""Platform for number (interval) integration."""

import logging

from propcache.api import cached_property

from homeassistant.components.number import RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .door import UnifiAccessDoor, DoorEntityType
from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add number entity for passed config entry."""
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = hass.data[DOMAIN]["coordinator"]

    entities = []
    
    if hub.supports_door_lock_rules:
        entities.extend([
            TemporaryLockRuleIntervalNumberEntity(door)
            for door in coordinator.data.values()
        ])
    
    # Add timing configuration entities for garage/gate doors
    entities.extend([
        DoorOpenTimeNumberEntity(hass, door)
        for door in coordinator.data.values()
        if door.entity_type in (DoorEntityType.GARAGE, DoorEntityType.GATE)
    ])
    
    entities.extend([
        DoorCloseTimeNumberEntity(hass, door)
        for door in coordinator.data.values()
        if door.entity_type in (DoorEntityType.GARAGE, DoorEntityType.GATE)
    ])
    
    async_add_entities(entities)


class TemporaryLockRuleIntervalNumberEntity(RestoreNumber):
    """Unifi Access Temporary Lock Rule Interval Interval."""

    _attr_translation_key = "door_lock_rule_interval"
    _attr_has_entity_name = True

    @cached_property
    def should_poll(self) -> bool:
        """Return whether entity should be polled."""
        return False

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


class DoorOpenTimeNumberEntity(RestoreNumber):
    """Number entity for configuring door open time for garage/gate covers."""

    _attr_translation_key = "door_open_time"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "s"

    @cached_property
    def should_poll(self) -> bool:
        """Return whether entity should be polled."""
        return False

    def __init__(self, hass: HomeAssistant, door: UnifiAccessDoor) -> None:
        """Initialize Door Open Time Number."""
        super().__init__()
        self.hass = hass
        self.door: UnifiAccessDoor = door
        self._attr_unique_id = f"door_open_time_{self.door.id}"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 120
        self._attr_native_step = 1

    @property
    def device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        
        # Try to restore from entity state first
        last_state = await self.async_get_last_number_data()
        if last_state and last_state.native_value is not None:
            self._attr_native_value = last_state.native_value
        else:
            # Fall back to storage
            door_timings = self.hass.data[DOMAIN].get("door_timings", {})
            timing = door_timings.get(self.door.id, {"open_time": 0})
            self._attr_native_value = timing["open_time"]

    async def async_set_native_value(self, value: float) -> None:
        """Set door open time."""
        self._attr_native_value = value
        
        # Save to storage
        door_timings = self.hass.data[DOMAIN].get("door_timings", {})
        if self.door.id not in door_timings:
            door_timings[self.door.id] = {"open_time": 0, "close_time": 0}
        door_timings[self.door.id]["open_time"] = int(value)
        
        store = self.hass.data[DOMAIN].get("store")
        if store:
            entity_types = self.hass.data[DOMAIN].get("entity_types", {})
            await store.async_save({
                "entity_types": entity_types,
                "door_timings": door_timings,
            })
        
        self.async_write_ha_state()


class DoorCloseTimeNumberEntity(RestoreNumber):
    """Number entity for configuring door close time for garage/gate covers."""

    _attr_translation_key = "door_close_time"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "s"

    @cached_property
    def should_poll(self) -> bool:
        """Return whether entity should be polled."""
        return False

    def __init__(self, hass: HomeAssistant, door: UnifiAccessDoor) -> None:
        """Initialize Door Close Time Number."""
        super().__init__()
        self.hass = hass
        self.door: UnifiAccessDoor = door
        self._attr_unique_id = f"door_close_time_{self.door.id}"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 120
        self._attr_native_step = 1

    @property
    def device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        
        # Try to restore from entity state first
        last_state = await self.async_get_last_number_data()
        if last_state and last_state.native_value is not None:
            self._attr_native_value = last_state.native_value
        else:
            # Fall back to storage
            door_timings = self.hass.data[DOMAIN].get("door_timings", {})
            timing = door_timings.get(self.door.id, {"close_time": 0})
            self._attr_native_value = timing["close_time"]

    async def async_set_native_value(self, value: float) -> None:
        """Set door close time."""
        self._attr_native_value = value
        
        # Save to storage
        door_timings = self.hass.data[DOMAIN].get("door_timings", {})
        if self.door.id not in door_timings:
            door_timings[self.door.id] = {"open_time": 0, "close_time": 0}
        door_timings[self.door.id]["close_time"] = int(value)
        
        store = self.hass.data[DOMAIN].get("store")
        if store:
            entity_types = self.hass.data[DOMAIN].get("entity_types", {})
            await store.async_save({
                "entity_types": entity_types,
                "door_timings": door_timings,
            })
        
        self.async_write_ha_state()

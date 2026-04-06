"""Platform for number (interval) integration."""

from homeassistant.components.number import RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry
from .const import DOMAIN, DOOR_TYPE_GARAGE, DOOR_TYPE_GATE
from .hub import DoorState

PARALLEL_UPDATES = 0


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

    known_timing_doors: set[str] = set()

    def _check_for_cover_doors() -> None:
        new_entities = []
        for door_id, door in data.coordinator.data.items():
            if door.entity_type in (DOOR_TYPE_GARAGE, DOOR_TYPE_GATE) and door_id not in known_timing_doors:
                known_timing_doors.add(door_id)
                new_entities.append(DoorOpenTimeNumberEntity(door))
                new_entities.append(DoorCloseTimeNumberEntity(door))
        if new_entities:
            async_add_entities(new_entities)

    _check_for_cover_doors()

    config_entry.async_on_unload(
        data.coordinator.async_add_listener(_check_for_cover_doors)
    )


class TemporaryLockRuleIntervalNumberEntity(RestoreNumber):
    """Unifi Access Temporary Lock Rule Interval."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = True
    _attr_native_step = 1
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

    async def async_set_native_value(self, value: float) -> None:
        """Select Door Lock Rule Interval (in minutes)."""
        self._attr_native_value = value
        self.door.lock_rule_interval = int(value)


class DoorOpenTimeNumberEntity(RestoreNumber):
    """Number entity for configuring auto-close delay after open for garage/gate covers."""

    _attr_has_entity_name = True
    _attr_native_step = 1
    _attr_native_min_value = 0
    _attr_native_max_value = 120
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_should_poll = False
    _attr_translation_key = "door_open_time"

    def __init__(self, door: DoorState) -> None:
        """Initialize Door Open Time."""
        super().__init__()
        self.door = door
        self._attr_unique_id = f"door_open_time_{door.id}"
        self._attr_native_value = door.open_time

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last value."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last and last.native_value is not None:
            self._attr_native_value = last.native_value
            self.door.open_time = int(last.native_value)

    async def async_set_native_value(self, value: float) -> None:
        """Set door open time."""
        self._attr_native_value = value
        self.door.open_time = int(value)


class DoorCloseTimeNumberEntity(RestoreNumber):
    """Number entity for configuring auto-close delay after close for garage/gate covers."""

    _attr_has_entity_name = True
    _attr_native_step = 1
    _attr_native_min_value = 0
    _attr_native_max_value = 120
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_should_poll = False
    _attr_translation_key = "door_close_time"

    def __init__(self, door: DoorState) -> None:
        """Initialize Door Close Time."""
        super().__init__()
        self.door = door
        self._attr_unique_id = f"door_close_time_{door.id}"
        self._attr_native_value = door.close_time

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last value."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last and last.native_value is not None:
            self._attr_native_value = last.native_value
            self.door.close_time = int(last.native_value)

    async def async_set_native_value(self, value: float) -> None:
        """Set door close time."""
        self._attr_native_value = value
        self.door.close_time = int(value)

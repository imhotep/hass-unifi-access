"""Platform for event integration."""

from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry
from .const import (
    ACCESS_ENTRY_EVENT,
    ACCESS_EXIT_EVENT,
    ACCESS_GENERIC_EVENT,
    DOORBELL_START_EVENT,
    DOORBELL_STOP_EVENT,
)
from .entity import UnifiAccessDoorDeviceMixin
from .hub import DoorState

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add event entity for passed config entry."""
    data = config_entry.runtime_data

    if not data.hub.use_polling:
        doors = data.coordinator.data.values()
        async_add_entities(
            entity
            for door in doors
            for entity in (AccessEventEntity(door), DoorbellPressedEventEntity(door))
        )


class _UnifiAccessEventEntity(UnifiAccessDoorDeviceMixin, EventEntity):
    """Base class for Unifi Access event entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _event_name: str

    def __init__(self, door: DoorState) -> None:
        """Initialize event entity."""
        self.door = door
        self._attr_translation_placeholders = {"door_name": self.door.name}

    def _async_handle_event(self, event: str, event_attributes: dict[str, str]) -> None:
        """Handle incoming event from hub."""
        event_type = event_attributes.get("type", event)
        self._trigger_event(event_type, event_attributes)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register event listener with hub."""
        self.door.add_event_listener(self._event_name, self._async_handle_event)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister event listener."""
        await super().async_will_remove_from_hass()
        self.door.remove_event_listener(self._event_name, self._async_handle_event)


class AccessEventEntity(_UnifiAccessEventEntity):
    """Authorized User Event Entity."""

    _attr_event_types = [ACCESS_ENTRY_EVENT, ACCESS_EXIT_EVENT, ACCESS_GENERIC_EVENT]  # noqa: RUF012
    _attr_translation_key = "access_event"
    _event_name = "access"

    def __init__(self, door: DoorState) -> None:
        """Initialize access event entity."""
        super().__init__(door)
        self._attr_unique_id = f"{self.door.id}_access"


class DoorbellPressedEventEntity(_UnifiAccessEventEntity):
    """Doorbell Press Event Entity."""

    _attr_device_class = EventDeviceClass.DOORBELL
    _attr_event_types = [DOORBELL_START_EVENT, DOORBELL_STOP_EVENT]  # noqa: RUF012
    _attr_translation_key = "doorbell_event"
    _event_name = "doorbell_press"

    def __init__(self, door: DoorState) -> None:
        """Initialize doorbell event entity."""
        super().__init__(door)
        self._attr_unique_id = f"{self.door.id}_doorbell_press"

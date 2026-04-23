"""Base entities for the Unifi Access integration."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UnifiAccessCoordinator
from .hub import DoorState


class UnifiAccessDoorDeviceMixin:
    """Mixin providing device_info for any entity linked to a door."""

    door: DoorState

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this door."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )


class UnifiAccessDoorEntity(
    UnifiAccessDoorDeviceMixin,
    CoordinatorEntity[UnifiAccessCoordinator[dict[str, DoorState]]],
):
    """Base entity for a Unifi Access door bound to a coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: UnifiAccessCoordinator[dict[str, DoorState]], door: DoorState
    ) -> None:
        """Initialize the base door entity."""
        super().__init__(coordinator, context=door.id)
        self.door = door


def manage_door_entities(
    config_entry: ConfigEntry,
    coordinator: UnifiAccessCoordinator[dict[str, DoorState]],
    async_add_entities: AddConfigEntryEntitiesCallback,
    should_include: Callable[[DoorState], bool],
    build_entities: Callable[[str], Iterable[Entity]],
) -> None:
    """Add and remove door-linked entities as coordinator data changes."""
    entity_registry = er.async_get(coordinator.hass)
    active_entities: dict[str, list[Entity]] = {}

    def _sync_entities() -> None:
        for door_id in list(active_entities):
            door = coordinator.data.get(door_id)
            if door is not None and should_include(door):
                continue

            for entity in active_entities.pop(door_id):
                if entity.entity_id:
                    entity_registry.async_remove(entity.entity_id)
                else:
                    entity.async_remove()

        new_entities: list[Entity] = []
        for door_id, door in coordinator.data.items():
            if not should_include(door) or door_id in active_entities:
                continue

            entities = list(build_entities(door_id))
            active_entities[door_id] = entities
            new_entities.extend(entities)

        if new_entities:
            async_add_entities(new_entities)

    _sync_entities()
    config_entry.async_on_unload(coordinator.async_add_listener(_sync_entities))

"""Base entities for the Unifi Access integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
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


class UnifiAccessDoorEntity(UnifiAccessDoorDeviceMixin, CoordinatorEntity[UnifiAccessCoordinator[dict[str, DoorState]]]):
    """Base entity for a Unifi Access door bound to a coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: UnifiAccessCoordinator[dict[str, DoorState]], door: DoorState) -> None:
        """Initialize the base door entity."""
        super().__init__(coordinator, context=door.id)
        self.door = door

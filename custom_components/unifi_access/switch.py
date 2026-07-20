"""Platform for switch integration."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from unifi_access_api import EmergencyStatus

from . import UnifiAccessConfigEntry, UnifiAccessData
from .const import DOMAIN
from .coordinator import UnifiAccessCoordinator
from .entity import UnifiAccessDoorEntity, manage_door_entities
from .hub import UnifiAccessHub

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add switch entity for passed config entry."""
    data = config_entry.runtime_data
    async_add_entities(
        [
            EmergencySwitch(
                data.hub,
                data.emergency_coordinator,
                field="evacuation",
                unique_id="unifi_access_all_doors_evacuation",
                translation_key="evacuation",
            ),
            EmergencySwitch(
                data.hub,
                data.emergency_coordinator,
                field="lockdown",
                unique_id="unifi_access_all_doors_lockdown",
                translation_key="lockdown",
            ),
        ]
    )
    manage_door_entities(
        config_entry,
        data.coordinator,
        async_add_entities,
        lambda door: door.has_face_unlock,
        lambda door_id: [FaceUnlockSwitch(data, door_id)],
    )


class EmergencySwitch(CoordinatorEntity, SwitchEntity):
    """Unifi Access Emergency Switch (Evacuation / Lockdown)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hub: UnifiAccessHub,
        coordinator: UnifiAccessCoordinator[EmergencyStatus],
        *,
        field: str,
        unique_id: str,
        translation_key: str,
    ) -> None:
        """Initialize Unifi Access Emergency Switch."""
        super().__init__(coordinator, context=field)
        self.hub = hub
        self._field = field
        self._attr_unique_id = unique_id
        self._attr_translation_key = translation_key

    @property
    def device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "unifi_access_all_doors")},
            name="All Doors",
            model="UAH",
            manufacturer="Unifi",
        )

    @property
    def is_on(self) -> bool:
        """Get switch status."""
        return bool(getattr(self.hub, self._field))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off emergency mode."""
        await self.hub.async_set_emergency_status(**{self._field: False})

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on emergency mode."""
        await self.hub.async_set_emergency_status(**{self._field: True})


class FaceUnlockSwitch(UnifiAccessDoorEntity, SwitchEntity):
    """Switch to enable or disable face unlock on a UniFi reader device."""

    _attr_has_entity_name = True
    _attr_translation_key = "face_unlock"
    _attr_icon = "mdi:face-recognition"

    def __init__(self, data: UnifiAccessData, door_id: str) -> None:
        """Initialize the face unlock switch."""
        super().__init__(data.coordinator, data.coordinator.data[door_id])
        self._data = data
        self._attr_unique_id = f"{door_id}_face_unlock"

    @property
    def is_on(self) -> bool:
        """Return True when face unlock is enabled on the device."""
        settings = self.door.device_settings
        return settings is not None and settings.access_methods.face.is_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable face unlock."""
        await self._data.hub.async_set_face_unlock(self.door.id, enabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable face unlock."""
        await self._data.hub.async_set_face_unlock(self.door.id, enabled=False)

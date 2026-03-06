"""Platform for switch integration."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import UnifiAccessConfigEntry
from .const import DOMAIN
from .hub import UnifiAccessHub


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


class EmergencySwitch(CoordinatorEntity, SwitchEntity):
    """Unifi Access Emergency Switch (Evacuation / Lockdown)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hub: UnifiAccessHub,
        coordinator,
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
        return getattr(self.hub, self._field)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off emergency mode."""
        await self.hub.async_set_emergency_status(**{self._field: False})

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on emergency mode."""
        await self.hub.async_set_emergency_status(**{self._field: True})

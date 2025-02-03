"""Platform for switch integration."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UnifiAccessEvacuationAndLockdownSwitchCoordinator
from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add switch entity for passed config entry."""
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]

    coordinator: UnifiAccessEvacuationAndLockdownSwitchCoordinator = (
        UnifiAccessEvacuationAndLockdownSwitchCoordinator(hass, hub)
    )

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [
            EvacuationSwitch(hass, hub, coordinator),
            LockdownSwitch(hass, hub, coordinator),
        ]
    )


class EvacuationSwitch(CoordinatorEntity, SwitchEntity):
    """Unifi Access Evacuation Switch."""

    _attr_translation_key = "evacuation"
    _attr_has_entity_name = True
    should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        hub: UnifiAccessHub,
        coordinator: UnifiAccessEvacuationAndLockdownSwitchCoordinator,
    ) -> None:
        """Initialize Unifi Access Evacuation Switch."""
        super().__init__(coordinator, context="evacuation")
        self.hass = hass
        self.hub = hub
        self._is_on = self.hub.evacuation
        self._attr_unique_id = "unifi_access_all_doors_evacuation"

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Evacuation Switch device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "unifi_access_all_doors")},
            name="All Doors",
            model="UAH",
            manufacturer="Unifi",
        )

    @property
    def is_on(self) -> bool:
        """Get Unifi Access Evacuation Switch status."""
        return self.hub.evacuation

    async def async_turn_off(self, **kwargs: Any) -> None:
        "Turn off Evacuation."
        await self.hass.async_add_executor_job(
            self.hub.set_doors_emergency_status, {"evacuation": False}
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        "Turn off Evacuation."
        await self.hass.async_add_executor_job(
            self.hub.set_doors_emergency_status, {"evacuation": True}
        )

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Evacuation Switch updates from coordinator."""
        self._attr_is_on = self.hub.evacuation
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Evacuation Switch to Home Assistant."""
        await super().async_added_to_hass()
        self.hub.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Evacuation Switch from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.hub.remove_callback(self.async_write_ha_state)


class LockdownSwitch(CoordinatorEntity, SwitchEntity):
    """Unifi Access Lockdown Switch."""

    _attr_translation_key = "lockdown"
    _attr_has_entity_name = True
    should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        hub: UnifiAccessHub,
        coordinator: UnifiAccessEvacuationAndLockdownSwitchCoordinator,
    ) -> None:
        """Initialize Unifi Access Lockdown Switch."""
        super().__init__(coordinator, context="lockdown")
        self.hass = hass
        self.hub = hub
        self.coordinator = coordinator
        self._attr_unique_id = "unifi_access_all_doors_lockdown"
        self._is_on = self.hub.lockdown

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Lockdown Switch device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "unifi_access_all_doors")},
            name="All Doors",
            model="UAH",
            manufacturer="Unifi",
        )

    @property
    def is_on(self) -> bool:
        """Get Unifi Access Lockdown Switch status."""
        return self.hub.lockdown

    async def async_turn_off(self, **kwargs: Any) -> None:
        "Turn off Evacuation."
        await self.hass.async_add_executor_job(
            self.hub.set_doors_emergency_status, {"lockdown": False}
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        "Turn off Evacuation."
        await self.hass.async_add_executor_job(
            self.hub.set_doors_emergency_status, {"lockdown": True}
        )

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Lockdown Switch updates from coordinator."""
        self._attr_is_on = self.hub.lockdown
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Lockdown Switch to Home Assistant."""
        await super().async_added_to_hass()
        self.hub.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Lockdown Switch from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.hub.remove_callback(self.async_write_ha_state)

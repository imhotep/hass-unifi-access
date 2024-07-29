"""Platform for switch integration."""

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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Binary Sensor for passed config entry."""
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
        self._attr_name = "Evacuation"

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Evacuation Switch device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "unifi_access_all_doors")},
            name="All Doors",
            model="UAH",
            manufacturer="Unifi",
        )

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
        """Handle Unifi Access Door Lock updates from coordinator."""
        self._attr_is_on = self.hub.evacuation
        self.async_write_ha_state()


class LockdownSwitch(CoordinatorEntity, SwitchEntity):
    """Unifi Access Lockdown Switch."""

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
        self._attr_name = "Lockdown"

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Lockdown Switch device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "unifi_access_all_doors")},
            name="All Doors",
            model="UAH",
            manufacturer="Unifi",
        )

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
        """Handle Unifi Access Door Lock updates from coordinator."""
        self._attr_is_on = self.hub.lockdown
        self.async_write_ha_state()

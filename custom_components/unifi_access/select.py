"""Platform for select integration."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UnifiAccessCoordinator
from .door import UnifiAccessDoor
from .hub import UnifiAccessHub


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add select entity for passed config entry."""
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = hass.data[DOMAIN]["coordinator"]

    if hub.supports_door_lock_rules:
        async_add_entities(
            [
                TemporaryLockRuleSelectEntity(coordinator, door_id)
                for door_id in coordinator.data
            ]
        )


class TemporaryLockRuleSelectEntity(CoordinatorEntity, SelectEntity):
    """Unifi Access Temporary Lock Rule Select."""

    _attr_translation_key = "door_lock_rules"
    _attr_has_entity_name = True
    should_poll = False

    def __init__(
        self,
        coordinator: UnifiAccessCoordinator,
        door_id: str,
    ) -> None:
        """Initialize Unifi Access Door Lock Rule."""
        super().__init__(coordinator, context="lock_rule")
        self.door: UnifiAccessDoor = self.coordinator.data[door_id]
        self._attr_unique_id = f"door_lock_rule_{door_id}"
        self._attr_options = [
            "",
            "keep_lock",
            "keep_unlock",
            "custom",
            "reset",
            "lock_early",
        ]
        self._update_options()

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Door Lock device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    @property
    def current_option(self) -> str:
        "Get current option."
        return self.door.lock_rule

    def _update_options(self):
        "Update Door Lock Rules."
        self._attr_current_option = self.coordinator.data[self.door.id].lock_rule
        if (
            self._attr_current_option != "schedule"
            and "lock_early" in self._attr_options
        ):
            self._attr_options.remove("lock_early")
        else:
            self._attr_options.append("lock_early")

    async def async_select_option(self, option: str) -> None:
        "Select Door Lock Rule."
        await self.hass.async_add_executor_job(self.door.set_lock_rule, option)

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Door Rule Lock Select to Home Assistant."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Rule Lock Select from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Door Lock updates from coordinator."""
        self._update_options()
        self.async_write_ha_state()

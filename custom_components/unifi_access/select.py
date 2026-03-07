"""Platform for select integration."""

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry, UnifiAccessData
from .entity import UnifiAccessDoorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add select entity for passed config entry."""
    data = config_entry.runtime_data

    if data.hub.supports_door_lock_rules:
        async_add_entities(
            [
                TemporaryLockRuleSelectEntity(data, door_id)
                for door_id in data.coordinator.data
            ]
        )


class TemporaryLockRuleSelectEntity(UnifiAccessDoorEntity, SelectEntity):
    """Unifi Access Temporary Lock Rule Select."""

    _attr_translation_key = "door_lock_rules"

    def __init__(self, data: UnifiAccessData, door_id: str) -> None:
        """Initialize Unifi Access Door Lock Rule."""
        super().__init__(data.coordinator, data.coordinator.data[door_id])
        self._data = data
        self._attr_unique_id = f"door_lock_rule_{door_id}"
        self._update_options()

    @property
    def current_option(self) -> str:
        """Get current option."""
        return self.door.lock_rule

    def _update_options(self) -> None:
        """Update Door Lock Rules without duplications."""
        self._attr_current_option = self.coordinator.data[self.door.id].lock_rule

        base_options = [
            "",
            "keep_lock",
            "keep_unlock",
            "custom",
            "reset",
        ]

        if self._attr_current_option == "schedule":
            base_options.append("lock_early")

        self._attr_options = base_options

    async def async_select_option(self, option: str) -> None:
        """Select Door Lock Rule."""
        if not option:
            return
        await self._data.hub.async_set_lock_rule(self.door.id, option)

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Door Lock updates from coordinator."""
        self._update_options()
        self.async_write_ha_state()

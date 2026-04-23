"""Platform for select integration."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry, UnifiAccessData
from .const import DOOR_TYPES
from .entity import UnifiAccessDoorEntity

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add select entity for passed config entry."""
    data = config_entry.runtime_data

    entities: list[SelectEntity] = []

    if data.hub.supports_door_lock_rules:
        entities.extend(
            TemporaryLockRuleSelectEntity(data, door_id)
            for door_id in data.coordinator.data
        )

    async_add_entities(entities)

    # Track known UGT doors and add EntityTypeSelect once hub mapping is known.
    known_ugt_doors: set[str] = set()

    def _check_for_new_ugt_doors() -> None:
        new_entities = []
        for door_id, door in data.coordinator.data.items():
            if door.hub_type == "UGT" and door_id not in known_ugt_doors:
                known_ugt_doors.add(door_id)
                _LOGGER.debug(
                    "Discovered UGT door %s (%s), adding EntityTypeSelect",
                    door.name,
                    door_id,
                )
                new_entities.append(EntityTypeSelect(data, door_id))
        if new_entities:
            async_add_entities(new_entities)

    _check_for_new_ugt_doors()

    config_entry.async_on_unload(
        data.coordinator.async_add_listener(_check_for_new_ugt_doors)
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

    def _update_options(self) -> None:
        """Update Door Lock Rules without duplications."""
        lock_rule = self.coordinator.data[self.door.id].lock_rule
        self._attr_current_option = "" if lock_rule == "reset" else lock_rule

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
        if option == "reset":
            self._attr_current_option = ""
            self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Door Lock updates from coordinator."""
        self._update_options()
        self.async_write_ha_state()


class EntityTypeSelect(UnifiAccessDoorEntity, SelectEntity):
    """Select entity for choosing the HA entity type for a UGT door."""

    _attr_translation_key = "entity_type"
    _attr_options = DOOR_TYPES

    def __init__(self, data: UnifiAccessData, door_id: str) -> None:
        """Initialize EntityTypeSelect."""
        super().__init__(data.coordinator, data.coordinator.data[door_id])
        self._data = data
        self._attr_unique_id = f"{door_id}_entity_type"
        self._attr_current_option = self.door.entity_type

    async def async_select_option(self, option: str) -> None:
        """Persist the chosen entity type and update door state."""
        old_type = self.door.entity_type
        if option == old_type:
            return

        # Persist to storage
        self.door.entity_type = option
        self._attr_current_option = option
        stored: dict[str, str] = {}
        for door_id, door_state in self._data.coordinator.data.items():
            stored[door_id] = door_state.entity_type
        await self._data.store.async_save(stored)

        _LOGGER.debug(
            "Door %s entity type changed from %s to %s",
            self.door.name,
            old_type,
            option,
        )
        self._data.coordinator.async_set_updated_data(self._data.coordinator.data)

    def _handle_coordinator_update(self) -> None:
        """Sync current option from door state on coordinator update."""
        self._attr_current_option = self.door.entity_type
        self.async_write_ha_state()

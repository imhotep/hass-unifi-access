"""Platform for select integration."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry, UnifiAccessData
from .const import DOMAIN, DOOR_TYPE_GARAGE, DOOR_TYPE_GATE, DOOR_TYPE_LOCK, DOOR_TYPES
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

    # EntityTypeSelect entities are deferred: hub_type is only populated
    # after WebSocket device update messages arrive post-startup.
    # Track known doors and add EntityTypeSelect when hub_type is discovered.
    known_ugt_doors: set[str] = set()

    def _check_for_new_ugt_doors() -> None:
        new_entities = []
        for door_id, door in data.coordinator.data.items():
            if door.hub_type == "UGT" and door_id not in known_ugt_doors:
                known_ugt_doors.add(door_id)
                _LOGGER.debug("Discovered UGT door %s (%s), adding EntityTypeSelect", door.name, door_id)
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
    _attr_options = DOOR_TYPES  # noqa: RUF012

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
        self.async_write_ha_state()

        old_is_cover = old_type in (DOOR_TYPE_GARAGE, DOOR_TYPE_GATE)
        new_is_cover = option in (DOOR_TYPE_GARAGE, DOOR_TYPE_GATE)

        if old_is_cover != new_is_cover:
            await self._swap_entities(old_is_cover)
        elif new_is_cover:
            await self._reload_cover_platform()

    async def _swap_entities(self, old_is_cover: bool) -> None:
        """Swap between lock and cover entities."""
        registry = er.async_get(self.hass)

        # Remove stale registry entries BEFORE unloading (while entities are
        # still active) so HA creates fresh entries on reload.
        if old_is_cover:
            # cover → lock: remove cover + number + button entries
            for platform, uid in [
                ("cover", f"{self.door.id}_cover"),
                ("number", f"door_open_time_{self.door.id}"),
                ("number", f"door_close_time_{self.door.id}"),
                ("button", f"{self.door.id}_clear_obstruction"),
            ]:
                entity_id = registry.async_get_entity_id(platform, DOMAIN, uid)
                if entity_id:
                    registry.async_remove(entity_id)
        else:
            # lock → cover: remove lock entry and any stale cover entry
            for platform, uid in [
                ("lock", self.door.id),
                ("cover", f"{self.door.id}_cover"),
            ]:
                entity_id = registry.async_get_entity_id(platform, DOMAIN, uid)
                if entity_id:
                    registry.async_remove(entity_id)

        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            entry = entries[0]
            await self.hass.config_entries.async_unload_platforms(
                entry, [Platform.LOCK, Platform.COVER, Platform.NUMBER, Platform.BUTTON]
            )
            await self.hass.config_entries.async_forward_entry_setups(
                entry, [Platform.LOCK, Platform.COVER, Platform.NUMBER, Platform.BUTTON]
            )

    async def _reload_cover_platform(self) -> None:
        """Reload the cover platform (garage ↔ gate switch)."""
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            entry = entries[0]
            # Remove the cover entry so it's recreated fresh with the correct
            # device_class rather than inheriting a stale/disabled registry entry.
            registry = er.async_get(self.hass)
            entity_id = registry.async_get_entity_id("cover", DOMAIN, f"{self.door.id}_cover")
            if entity_id:
                registry.async_remove(entity_id)
            await self.hass.config_entries.async_unload_platforms(entry, [Platform.COVER])
            await self.hass.config_entries.async_forward_entry_setups(entry, [Platform.COVER])

    def _handle_coordinator_update(self) -> None:
        """Sync current option from door state on coordinator update."""
        self._attr_current_option = self.door.entity_type
        self.async_write_ha_state()

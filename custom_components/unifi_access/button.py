"""Platform for button integration."""

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry, UnifiAccessData
from .const import DOOR_TYPE_GARAGE, DOOR_TYPE_GATE
from .entity import UnifiAccessDoorEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add button entities for garage/gate typed doors."""
    data = config_entry.runtime_data

    known_doors: set[str] = set()

    def _check_for_cover_doors() -> None:
        new_entities = []
        for door_id, door in data.coordinator.data.items():
            if door.entity_type in (DOOR_TYPE_GARAGE, DOOR_TYPE_GATE) and door_id not in known_doors:
                known_doors.add(door_id)
                new_entities.append(ClearObstructionButton(data, door_id))
        if new_entities:
            async_add_entities(new_entities)

    _check_for_cover_doors()

    config_entry.async_on_unload(
        data.coordinator.async_add_listener(_check_for_cover_doors)
    )


class ClearObstructionButton(UnifiAccessDoorEntity, ButtonEntity):
    """Button to manually clear the obstruction flag on a cover door."""

    _attr_translation_key = "clear_obstruction"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, data: UnifiAccessData, door_id: str) -> None:
        """Initialize ClearObstructionButton."""
        super().__init__(data.coordinator, data.coordinator.data[door_id])
        self._data = data
        self._attr_unique_id = f"{door_id}_clear_obstruction"

    async def async_press(self) -> None:
        """Clear the obstruction flag and notify coordinator."""
        self.door.obstruction_detected = False
        self._data.coordinator.async_set_updated_data(self._data.coordinator.data)

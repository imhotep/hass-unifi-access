"""Platform for button integration."""

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry, UnifiAccessData
from .const import (
    DOOR_TYPE_GARAGE,
    DOOR_TYPE_GATE,
    GATE_DIRECTION_IN,
    GATE_DIRECTION_OUT,
    HUB_TYPE_UGT,
)
from .entity import UnifiAccessDoorEntity, manage_door_entities

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add button entities for garage/gate typed doors."""
    data = config_entry.runtime_data
    manage_door_entities(
        config_entry,
        data.coordinator,
        async_add_entities,
        lambda door: door.entity_type in (DOOR_TYPE_GARAGE, DOOR_TYPE_GATE),
        lambda door_id: [ClearObstructionButton(data, door_id)],
    )
    manage_door_entities(
        config_entry,
        data.coordinator,
        async_add_entities,
        lambda door: door.hub_type == HUB_TYPE_UGT and door.double_driveway_mode,
        lambda door_id: [
            OpenGateDirectionButton(data, door_id, direction=GATE_DIRECTION_IN),
            OpenGateDirectionButton(data, door_id, direction=GATE_DIRECTION_OUT),
        ],
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


class OpenGateDirectionButton(UnifiAccessDoorEntity, ButtonEntity):
    """Trigger one gate motor on a double-driveway UGT hub (in or out)."""

    def __init__(self, data: UnifiAccessData, door_id: str, *, direction: str) -> None:
        """Initialize OpenGateDirectionButton."""
        super().__init__(data.coordinator, data.coordinator.data[door_id])
        self._data = data
        self._direction = direction
        self._attr_unique_id = f"{door_id}_open_gate_{direction}"
        self._attr_translation_key = (
            "open_gate_in" if direction == GATE_DIRECTION_IN else "open_gate_out"
        )
        self._attr_icon = (
            "mdi:arrow-down-bold-box-outline"
            if direction == GATE_DIRECTION_IN
            else "mdi:arrow-up-bold-box-outline"
        )

    async def async_press(self) -> None:
        """Trigger the gate motor for this direction."""
        await self._data.hub.async_open_door_direction(self.door.id, self._direction)

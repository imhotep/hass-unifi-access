"""Platform for cover integration (garage doors and gates)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from . import UnifiAccessConfigEntry, UnifiAccessData
from .const import DOOR_TYPE_GARAGE, DOOR_TYPE_GATE
from .entity import UnifiAccessDoorEntity, manage_door_entities

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add cover entities for garage/gate typed doors."""
    data = config_entry.runtime_data
    manage_door_entities(
        config_entry,
        data.coordinator,
        async_add_entities,
        lambda door: door.entity_type in (DOOR_TYPE_GARAGE, DOOR_TYPE_GATE),
        lambda door_id: [UnifiAccessCoverEntity(data, door_id)],
    )


class UnifiAccessCoverEntity(UnifiAccessDoorEntity, CoverEntity):
    """Unifi Access Cover Entity (garage door or gate)."""

    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
    _attr_name = None

    def __init__(self, data: UnifiAccessData, door_id: str) -> None:
        """Initialize the cover entity."""
        super().__init__(data.coordinator, data.coordinator.data[door_id])
        self._data = data
        self._attr_unique_id = f"{door_id}_cover"

        self._is_opening = False
        self._is_closing = False
        self._last_trigger_time: float = 0
        self._operation_timer_cancel = None
        self._debounce_task: asyncio.Task | None = None
        self._last_sensor_state: bool | None = None

    @property
    def device_class(self) -> CoverDeviceClass:
        """Return device class based on entity type."""
        if self.door.entity_type == DOOR_TYPE_GATE:
            return CoverDeviceClass.GATE
        return CoverDeviceClass.GARAGE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {"obstruction_detected": self.door.obstruction_detected}

    @property
    def is_closed(self) -> bool | None:
        """Return whether the cover is closed."""
        if self._is_opening or self._is_closing:
            return None
        return not self.door.is_open and self.door.is_locked

    @property
    def is_opening(self) -> bool:
        """Return True while opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return True while closing."""
        return self._is_closing

    def _cancel_operation_timer(self) -> None:
        """Cancel any running operation timer."""
        if self._operation_timer_cancel:
            self._operation_timer_cancel()
            self._operation_timer_cancel = None

    def _cancel_debounce_task(self) -> None:
        """Cancel any running debounce task."""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
            self._debounce_task = None

    def _start_opening_timer(self, open_time: int) -> None:
        """Start timer for opening operation."""
        self._cancel_operation_timer()
        when = dt_util.utcnow() + timedelta(seconds=open_time)
        self._operation_timer_cancel = async_track_point_in_time(
            self.hass, self._opening_timer_finished, when
        )

    def _start_closing_timer(self, close_time: int) -> None:
        """Start timer for closing operation."""
        self._cancel_operation_timer()
        when = dt_util.utcnow() + timedelta(seconds=close_time)
        self._operation_timer_cancel = async_track_point_in_time(
            self.hass, self._closing_timer_finished, when
        )

    @callback
    def _opening_timer_finished(self, now: datetime) -> None:
        """Handle opening timer expiration — obstruct if door still closed."""
        sensor_closed = not self.door.is_open and self.door.is_locked
        if sensor_closed:
            _LOGGER.warning(
                "Door %s opening timer expired but door is still closed - obstructed",
                self.door.name,
            )
            self.door.obstruction_detected = True
        else:
            self.door.obstruction_detected = False
        self._is_opening = False
        self._operation_timer_cancel = None
        self.async_write_ha_state()

    @callback
    def _closing_timer_finished(self, now: datetime) -> None:
        """Handle closing timer expiration — obstruct if door still open."""
        sensor_closed = not self.door.is_open and self.door.is_locked
        if not sensor_closed:
            _LOGGER.warning(
                "Door %s closing timer expired but door is still open - obstructed",
                self.door.name,
            )
            self.door.obstruction_detected = True
        else:
            self.door.obstruction_detected = False
        self._is_closing = False
        self._operation_timer_cancel = None
        self.async_write_ha_state()

    async def _debounced_sensor_check(self, sensor_closed: bool) -> None:
        """Wait 500ms then handle sensor change if state is still stable."""
        await asyncio.sleep(0.5)
        current_closed = not self.door.is_open and self.door.is_locked
        if current_closed == sensor_closed:
            await self._handle_sensor_change(sensor_closed)

    async def _handle_sensor_change(self, sensor_closed: bool) -> None:
        """React to a confirmed door sensor state change."""
        _LOGGER.debug(
            "Door %s sensor: %s (opening=%s closing=%s)",
            self.door.name,
            "closed" if sensor_closed else "open",
            self._is_opening,
            self._is_closing,
        )
        if not sensor_closed and not self._is_opening and not self._is_closing:
            # Opened externally
            open_time = self.door.open_time
            if open_time > 0:
                _LOGGER.info(
                    "Door %s opened externally, starting open timer", self.door.name
                )
                self._is_opening = True
                self.door.obstruction_detected = False
                self.async_write_ha_state()
                self._start_opening_timer(open_time)
        elif sensor_closed and self._is_opening:
            # Closed unexpectedly while opening
            _LOGGER.warning(
                "Door %s closed unexpectedly during opening - obstructed",
                self.door.name,
            )
            self._cancel_operation_timer()
            self._is_opening = False
            self.door.obstruction_detected = True
            self.async_write_ha_state()
        elif sensor_closed and self._is_closing:
            # Closed successfully before timer expired
            _LOGGER.debug("Door %s closed successfully", self.door.name)
            self._cancel_operation_timer()
            self._is_closing = False
            self.door.obstruction_detected = False
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Initialise sensor state baseline."""
        await super().async_added_to_hass()
        self._last_sensor_state = not self.door.is_open and self.door.is_locked

    async def async_will_remove_from_hass(self) -> None:
        """Clean up timers on removal."""
        self._cancel_operation_timer()
        self._cancel_debounce_task()
        await super().async_will_remove_from_hass()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover — momentary unlock trigger."""
        now = dt_util.now().timestamp()
        if now - self._last_trigger_time < 1.0:
            _LOGGER.debug("Door %s trigger rate limited", self.door.name)
            return
        self._last_trigger_time = now
        self.door.obstruction_detected = False

        await self._data.hub.client.unlock_door(self.door.id)

        # Always start the opening timer on an explicit command — sensor state
        # at trigger time may be mid-travel from a preceding close cycle.
        open_time = self.door.open_time
        if open_time > 0:
            _LOGGER.debug(
                "Door %s starting open operation (%ds)", self.door.name, open_time
            )
            self._cancel_operation_timer()
            self._is_opening = True
            self._is_closing = False
            self._start_opening_timer(open_time)
        else:
            self._is_opening = False
            self._is_closing = False
            self._cancel_operation_timer()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover — same momentary unlock trigger activates the motor."""
        now = dt_util.now().timestamp()
        if now - self._last_trigger_time < 1.0:
            _LOGGER.debug("Door %s trigger rate limited", self.door.name)
            return
        self._last_trigger_time = now
        self.door.obstruction_detected = False

        await self._data.hub.client.unlock_door(self.door.id)

        # Always start the closing timer on an explicit command — sensor state
        # at trigger time may be mid-travel from a preceding open cycle.
        close_time = self.door.close_time
        if close_time > 0:
            _LOGGER.debug(
                "Door %s starting close operation (%ds)", self.door.name, close_time
            )
            self._cancel_operation_timer()
            self._is_opening = False
            self._is_closing = True
            self._start_closing_timer(close_time)
        else:
            self._is_opening = False
            self._is_closing = False
            self._cancel_operation_timer()
        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator updates — detect sensor changes with debouncing."""
        current_sensor_closed = not self.door.is_open and self.door.is_locked
        if (
            self._last_sensor_state is not None
            and current_sensor_closed != self._last_sensor_state
        ):
            self._cancel_debounce_task()
            self._debounce_task = asyncio.ensure_future(
                self._debounced_sensor_check(current_sensor_closed)
            )
        self._last_sensor_state = current_sensor_closed
        self.async_write_ha_state()

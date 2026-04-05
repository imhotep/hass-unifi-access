"""Platform for cover integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from functools import cached_property
import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .door import UnifiAccessDoor, DoorEntityType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add cover entity for passed config entry."""

    coordinator = hass.data[DOMAIN]["coordinator"]

    # Only create cover entities for doors configured as garage or gate
    async_add_entities(
        UnifiGarageDoorCoverEntity(coordinator, key)
        for key in coordinator.data
        if coordinator.data[key].entity_type in (DoorEntityType.GARAGE, DoorEntityType.GATE)
    )


class UnifiGarageDoorCoverEntity(CoordinatorEntity, CoverEntity):
    """Unifi Access Garage/Gate Door Cover."""

    _attr_translation_key = "access_cover"
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator, door_id) -> None:
        """Initialize Unifi Access Garage Door Cover."""
        super().__init__(coordinator, context=door_id)
        self.door: UnifiAccessDoor = self.coordinator.data[door_id]
        self._attr_unique_id = f"{self.door.id}_cover"
        self._attr_translation_placeholders = {"door_name": self.door.name}
        
        # State machine variables
        self._is_opening = False
        self._is_closing = False
        self._obstruction_detected = False
        self._last_trigger_time: float = 0
        self._operation_timer_cancel = None
        self._debounce_task = None
        self._last_sensor_state: bool | None = None
        self._last_sensor_change_time: float = 0

    @property
    def device_class(self) -> CoverDeviceClass:
        """Return the device class based on entity_type."""
        if self.door.entity_type == DoorEntityType.GATE:
            return CoverDeviceClass.GATE
        return CoverDeviceClass.GARAGE

    @cached_property
    def supported_features(self) -> CoverEntityFeature:
        """Return supported features."""
        return CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    @cached_property
    def should_poll(self) -> bool:
        """Return whether entity should be polled."""
        return False

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Garage Door Cover device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "obstruction_detected": self._obstruction_detected,
        }
    
    def _get_timing_config(self) -> tuple[int, int]:
        """Get open and close time configuration from storage."""
        door_timings = self.hass.data[DOMAIN].get("door_timings", {})
        timing = door_timings.get(self.door.id, {"open_time": 0, "close_time": 0})
        return timing["open_time"], timing["close_time"]
    
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
    
    async def _debounced_sensor_check(self, sensor_closed: bool) -> None:
        """Debounce sensor changes to avoid false triggers from vibration."""
        await asyncio.sleep(0.5)  # 500ms debounce
        
        # After debounce, check if sensor state is stable
        current_sensor_closed = not self.door.is_open and self.door.is_locked
        if current_sensor_closed == sensor_closed:
            # Sensor is stable, process the change
            await self._handle_sensor_change(sensor_closed)
    
    async def _handle_sensor_change(self, sensor_closed: bool) -> None:
        """Handle door sensor state change after debouncing."""
        _LOGGER.debug(
            "Door %s sensor changed to %s (opening=%s, closing=%s)",
            self.door.name,
            "closed" if sensor_closed else "open",
            self._is_opening,
            self._is_closing,
        )
        
        # Out-of-band opening detection: sensor opens when we're not opening
        if not sensor_closed and not self._is_opening and not self._is_closing:
            _LOGGER.info("Door %s opened externally, entering opening state", self.door.name)
            open_time, _ = self._get_timing_config()
            if open_time > 0:
                self._is_opening = True
                self._obstruction_detected = False
                self.async_write_ha_state()
                self._start_opening_timer(open_time)
        
        # Unexpected close during opening = obstruction
        elif sensor_closed and self._is_opening:
            _LOGGER.warning("Door %s closed unexpectedly during opening - marking obstructed", self.door.name)
            self._cancel_operation_timer()
            self._is_opening = False
            self._obstruction_detected = True
            self.async_write_ha_state()
        
        # Expected close during closing = success
        elif sensor_closed and self._is_closing:
            _LOGGER.debug("Door %s closed successfully", self.door.name)
            self._cancel_operation_timer()
            self._is_closing = False
            self._obstruction_detected = False
            self.async_write_ha_state()
    
    @callback
    def _opening_timer_finished(self, now: datetime) -> None:
        """Handle opening timer expiration."""
        sensor_closed = not self.door.is_open and self.door.is_locked
        
        if sensor_closed:
            # Door should be open but sensor says closed = obstruction
            _LOGGER.warning("Door %s opening timer expired but door is still closed - marking obstructed", self.door.name)
            self._obstruction_detected = True
        else:
            _LOGGER.debug("Door %s opening completed successfully", self.door.name)
            self._obstruction_detected = False
        
        self._is_opening = False
        self._operation_timer_cancel = None
        self.async_write_ha_state()
    
    @callback
    def _closing_timer_finished(self, now: datetime) -> None:
        """Handle closing timer expiration."""
        sensor_closed = not self.door.is_open and self.door.is_locked
        
        if not sensor_closed:
            # Door should be closed but sensor says open = obstruction
            _LOGGER.warning("Door %s closing timer expired but door is still open - marking obstructed", self.door.name)
            self._obstruction_detected = True
        else:
            _LOGGER.debug("Door %s closing completed successfully", self.door.name)
            self._obstruction_detected = False
        
        self._is_closing = False
        self._operation_timer_cancel = None
        self.async_write_ha_state()
    
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

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Garage Door Cover to Home Assistant."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)
        # Initialize last sensor state
        self._last_sensor_state = not self.door.is_open and self.door.is_locked

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Garage Door Cover from Home Assistant."""
        self._cancel_operation_timer()
        self._cancel_debounce_task()
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover (trigger the door motor)."""
        # Rate limiting: 1 trigger per second
        now = dt_util.now().timestamp()
        if now - self._last_trigger_time < 1.0:
            _LOGGER.debug("Door %s trigger rate limited", self.door.name)
            return
        self._last_trigger_time = now
        
        # Clear obstruction on any trigger
        self._obstruction_detected = False
        
        # Trigger the door
        await self.hass.async_add_executor_job(self.door.unlock)
        
        # Get timing configuration
        open_time, _ = self._get_timing_config()
        
        # Determine new state based on current sensor
        sensor_closed = not self.door.is_open and self.door.is_locked
        
        if sensor_closed and open_time > 0:
            # Starting to open from closed position
            _LOGGER.debug("Door %s starting opening operation (%ds)", self.door.name, open_time)
            self._cancel_operation_timer()
            self._is_opening = True
            self._is_closing = False
            self._start_opening_timer(open_time)
        else:
            # No timing configured or door already open
            self._is_opening = False
            self._is_closing = False
            self._cancel_operation_timer()
        
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover (trigger the door motor)."""
        # Rate limiting: 1 trigger per second
        now = dt_util.now().timestamp()
        if now - self._last_trigger_time < 1.0:
            _LOGGER.debug("Door %s trigger rate limited", self.door.name)
            return
        self._last_trigger_time = now
        
        # Clear obstruction on any trigger
        self._obstruction_detected = False
        
        # Trigger the door
        await self.hass.async_add_executor_job(self.door.unlock)
        
        # Get timing configuration
        _, close_time = self._get_timing_config()
        
        # Determine new state based on current sensor
        sensor_closed = not self.door.is_open and self.door.is_locked
        
        if not sensor_closed and close_time > 0:
            # Starting to close from open position
            _LOGGER.debug("Door %s starting closing operation (%ds)", self.door.name, close_time)
            self._cancel_operation_timer()
            self._is_opening = False
            self._is_closing = True
            self._start_closing_timer(close_time)
        else:
            # No timing configured or door already closed
            self._is_opening = False
            self._is_closing = False
            self._cancel_operation_timer()
        
        self.async_write_ha_state()

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed (door is closed and locked)."""
        if self._is_opening or self._is_closing:
            return None  # Unknown during movement
        return not self.door.is_open and self.door.is_locked

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return self._is_closing

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Garage Door Cover updates from coordinator."""
        # Check for sensor state changes with debouncing
        current_sensor_closed = not self.door.is_open and self.door.is_locked
        
        if self._last_sensor_state is not None and current_sensor_closed != self._last_sensor_state:
            # Sensor state changed - start debounce
            self._cancel_debounce_task()
            self._debounce_task = asyncio.create_task(
                self._debounced_sensor_check(current_sensor_closed)
            )
        
        self._last_sensor_state = current_sensor_closed
        self.async_write_ha_state()

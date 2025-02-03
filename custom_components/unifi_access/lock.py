"""Platform for sensor integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .door import UnifiAccessDoor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add lock entity for passed config entry."""

    coordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities(
        UnifiDoorLockEntity(coordinator, key) for key in coordinator.data
    )


class UnifiDoorLockEntity(CoordinatorEntity, LockEntity):
    """Unifi Access Door Lock."""

    should_poll = False

    supported_features = LockEntityFeature.OPEN

    _attr_translation_key = "access_door"
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator, door_id) -> None:
        """Initialize Unifi Access Door Lock."""
        super().__init__(coordinator, context=id)
        self.door: UnifiAccessDoor = self.coordinator.data[door_id]
        self._attr_unique_id = self.door.id
        self._attr_translation_placeholders = {"door_name": self.door.name}

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Door Lock device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Door Lock to Home Assistant."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Door Lock from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock all or specified locks. A code to unlock the lock with may optionally be specified."""
        await self.hass.async_add_executor_job(self.door.unlock)

    async def async_open(self, **kwargs: Any) -> None:
        """Unlock all or specified locks. A code to unlock the lock with may optionally be specified."""
        await self.hass.async_add_executor_job(self.door.open)

    def lock(self, **kwargs: Any) -> None:
        """Lock all or specified locks. A code to lock the lock with may optionally be specified."""
        _LOGGER.warning("Locking is not supported by Unifi Access API")

    @property
    def is_locked(self) -> bool | None:
        """Get Unifi Access Door Lock locked status."""
        return self.door.is_locked

    @property
    def is_locking(self) -> bool | None:
        """Get Unifi Access Door Lock locking status."""
        return self.door.is_locking

    @property
    def is_unlocking(self) -> bool | None:
        """Get Unifi Access Door Lock unlocking status."""
        return self.door.is_unlocking

    def _handle_coordinator_update(self) -> None:
        """Handle Unifi Access Door Lock updates from coordinator."""
        self._attr_is_locked = self.door.is_locked
        self._attr_is_locking = self.door.is_locking
        self._attr_is_unlocking = self.door.is_unlocking
        self.async_write_ha_state()

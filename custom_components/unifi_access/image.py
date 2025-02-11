"""Platform for sensor integration."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .door import UnifiAccessDoor
from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add image entity for passed config entry."""

    coordinator = hass.data[DOMAIN]["coordinator"]
    verify_ssl = config_entry.options.get("verify_ssl", False)
    hub: UnifiAccessHub = hass.data[DOMAIN][config_entry.entry_id]
    if hub.use_polling is False:
        async_add_entities(
            UnifiDoorImageEntity(hass, verify_ssl, door, config_entry.data["api_token"])
            for door in coordinator.data.values()
        )


class UnifiDoorImageEntity(ImageEntity):
    """Unifi Access Door Image."""

    should_poll = False

    _attr_translation_key = "door_thumbnail"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, verify_ssl: bool, door, api_token) -> None:
        """Initialize Unifi Access Door Image."""
        super().__init__(hass, verify_ssl)
        self.door: UnifiAccessDoor = door
        self._attr_unique_id = self.door.id
        self._attr_translation_placeholders = {"door_name": self.door.name}

    @property
    def device_info(self) -> DeviceInfo:
        """Get Unifi Access Door Image device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.door.id)},
            name=self.door.name,
            model=self.door.hub_type,
            manufacturer="Unifi",
        )

    async def async_added_to_hass(self) -> None:
        """Add Unifi Access Door Image to Home Assistant."""
        await super().async_added_to_hass()
        self.door.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove Unifi Access Door Image from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.door.remove_callback(self.async_write_ha_state)

    @property
    def image_last_updated(self) -> datetime | None:
        """Get Unifi Access Door Image Last Updated."""
        return self.door.thumbnail_last_updated

    async def async_image(self) -> bytes | None:
        """Get Unifi Access Door Image Thumbnail."""
        return self.door.thumbnail

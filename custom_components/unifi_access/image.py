"""Platform for image integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiAccessConfigEntry
from .entity import UnifiAccessDoorEntity
from .hub import DoorState


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add image entity for passed config entry."""
    data = config_entry.runtime_data
    verify_ssl = config_entry.data["verify_ssl"]

    if not data.hub.use_polling:
        async_add_entities(
            UnifiDoorImageEntity(data.coordinator, hass, verify_ssl, door)
            for door in data.coordinator.data.values()
        )


class UnifiDoorImageEntity(UnifiAccessDoorEntity, ImageEntity):
    """Unifi Access Door Image."""

    _attr_translation_key = "door_thumbnail"

    def __init__(
        self, coordinator, hass: HomeAssistant, verify_ssl: bool, door: DoorState
    ) -> None:
        """Initialize Unifi Access Door Image."""
        UnifiAccessDoorEntity.__init__(self, coordinator, door)
        ImageEntity.__init__(self, hass, verify_ssl)
        self._attr_unique_id = self.door.id
        self._attr_translation_placeholders = {"door_name": self.door.name}

    @property
    def image_last_updated(self) -> datetime | None:
        """Get Unifi Access Door Image Last Updated."""
        return self.door.thumbnail_last_updated

    async def async_image(self) -> bytes | None:
        """Get Unifi Access Door Image Thumbnail."""
        return self.door.thumbnail

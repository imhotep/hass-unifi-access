"""Diagnostics support for UniFi Access."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import UnifiAccessConfigEntry

REDACT_CONFIG = {"api_token"}
REDACT_DOOR = {"full_name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: UnifiAccessConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data
    hub = data.hub

    doors = {
        door_id: {
            "id": state.id,
            "name": state.name,
            "hub_id": state.hub_id,
            "hub_type": state.hub_type,
            "is_locked": state.is_locked,
            "is_open": state.is_open,
            "lock_rule": state.lock_rule,
            "lock_rule_interval": state.lock_rule_interval,
            "doorbell_pressed": state.doorbell_pressed,
        }
        for door_id, state in hub.doors.items()
    }

    return {
        "config_entry": async_redact_data(dict(entry.data), REDACT_CONFIG),
        "use_polling": hub.use_polling,
        "supports_door_lock_rules": hub.supports_door_lock_rules,
        "evacuation": hub.evacuation,
        "lockdown": hub.lockdown,
        "doors": doors,
    }

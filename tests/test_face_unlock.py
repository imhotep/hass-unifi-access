"""Tests for FaceUnlockSwitch entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_access.const import DOMAIN

from .conftest import (
    MOCK_CONFIG,
    SAMPLE_DEVICE_DOOR_MAP,
    SAMPLE_DEVICES,
    SAMPLE_DEVICES_WITH_FACE,
    SAMPLE_DEVICE_SETTINGS_FACE_OFF,
    SAMPLE_DEVICE_SETTINGS_FACE_ON,
    SAMPLE_DOORS,
    SAMPLE_EMERGENCY_STATUS,
    SAMPLE_LOCK_RULE_STATUS,
)


def _make_mock_client(*, face_capable: bool = False) -> AsyncMock:
    client = AsyncMock()
    client.authenticate = AsyncMock()
    client.get_doors = AsyncMock(return_value=SAMPLE_DOORS)
    client.get_door_lock_rule = AsyncMock(return_value=SAMPLE_LOCK_RULE_STATUS)
    client.get_emergency_status = AsyncMock(return_value=SAMPLE_EMERGENCY_STATUS)
    client.set_emergency_status = AsyncMock()
    client.unlock_door = AsyncMock()
    devices = SAMPLE_DEVICES_WITH_FACE if face_capable else SAMPLE_DEVICES
    client.get_devices = AsyncMock(return_value=devices)
    device_door_map = {d.id: d.location_id for d in devices}
    client.get_device_door_map = AsyncMock(return_value=device_door_map)
    client.resolve_door_id = MagicMock(side_effect=device_door_map.get)
    client.get_device_settings = AsyncMock(return_value=SAMPLE_DEVICE_SETTINGS_FACE_OFF)
    client.put_device_settings = AsyncMock()
    client.start_websocket = MagicMock()
    client.close = AsyncMock()
    return client


async def _setup(hass: HomeAssistant, mock_client: AsyncMock) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="192.168.1.1",
        title="Unifi Access",
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.unifi_access.UnifiAccessApiClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.unifi_access.async_get_clientsession",
            return_value=AsyncMock(),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_face_unlock_switch_created_for_capable_device(
    hass: HomeAssistant,
) -> None:
    """FaceUnlockSwitch is created when the hub device has support_face capability."""
    mock_client = _make_mock_client(face_capable=True)
    await _setup(hass, mock_client)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, "door-001_face_unlock")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None


async def test_face_unlock_switch_not_created_for_incapable_device(
    hass: HomeAssistant,
) -> None:
    """FaceUnlockSwitch is NOT created when the device has no face capability."""
    mock_client = _make_mock_client(face_capable=False)
    await _setup(hass, mock_client)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, "door-001_face_unlock")
    assert entity_id is None


async def test_face_unlock_initial_state_off(hass: HomeAssistant) -> None:
    """Switch initial state reflects device settings (face disabled)."""
    mock_client = _make_mock_client(face_capable=True)
    mock_client.get_device_settings = AsyncMock(
        return_value=SAMPLE_DEVICE_SETTINGS_FACE_OFF
    )
    await _setup(hass, mock_client)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, "door-001_face_unlock")
    assert hass.states.get(entity_id).state == "off"


async def test_face_unlock_initial_state_on(hass: HomeAssistant) -> None:
    """Switch initial state reflects device settings (face enabled)."""
    mock_client = _make_mock_client(face_capable=True)
    mock_client.get_device_settings = AsyncMock(
        return_value=SAMPLE_DEVICE_SETTINGS_FACE_ON
    )
    await _setup(hass, mock_client)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, "door-001_face_unlock")
    assert hass.states.get(entity_id).state == "on"


async def test_turn_on_calls_put_device_settings(hass: HomeAssistant) -> None:
    """Turning on calls put_device_settings with face enabled=yes."""
    mock_client = _make_mock_client(face_capable=True)
    await _setup(hass, mock_client)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, "door-001_face_unlock")

    mock_client.put_device_settings.reset_mock()
    await hass.services.async_call(
        SWITCH_DOMAIN, "turn_on", {"entity_id": entity_id}, blocking=True
    )
    mock_client.put_device_settings.assert_called_once_with(
        "hub-intercom-001", {"face": {"enabled": "yes"}}
    )


async def test_turn_off_calls_put_device_settings(hass: HomeAssistant) -> None:
    """Turning off calls put_device_settings with face enabled=no."""
    mock_client = _make_mock_client(face_capable=True)
    mock_client.get_device_settings = AsyncMock(
        return_value=SAMPLE_DEVICE_SETTINGS_FACE_ON
    )
    await _setup(hass, mock_client)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, "door-001_face_unlock")

    mock_client.put_device_settings.reset_mock()
    await hass.services.async_call(
        SWITCH_DOMAIN, "turn_off", {"entity_id": entity_id}, blocking=True
    )
    mock_client.put_device_settings.assert_called_once_with(
        "hub-intercom-001", {"face": {"enabled": "no"}}
    )

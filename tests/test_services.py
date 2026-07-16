"""Tests for domain-level services registered in async_setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_access import UnifiAccessData, async_setup
from custom_components.unifi_access.const import DOMAIN

from .conftest import (
    MOCK_CONFIG,
    SAMPLE_DEVICE_DOOR_MAP,
    SAMPLE_DEVICES,
    SAMPLE_DOORS,
    SAMPLE_EMERGENCY_STATUS,
    SAMPLE_LOCK_RULE_STATUS,
)


def _make_mock_client() -> AsyncMock:
    client = AsyncMock()
    client.authenticate = AsyncMock()
    client.get_doors = AsyncMock(return_value=SAMPLE_DOORS)
    client.get_door_lock_rule = AsyncMock(return_value=SAMPLE_LOCK_RULE_STATUS)
    client.get_emergency_status = AsyncMock(return_value=SAMPLE_EMERGENCY_STATUS)
    client.get_devices = AsyncMock(return_value=SAMPLE_DEVICES)
    client.get_device_door_map = AsyncMock(return_value=SAMPLE_DEVICE_DOOR_MAP)
    client.resolve_door_id = MagicMock(side_effect=SAMPLE_DEVICE_DOOR_MAP.get)
    client.start_websocket = MagicMock()
    client.close = AsyncMock()
    client.update_user_status = AsyncMock()
    client.update_user_pin = AsyncMock()
    return client


async def _setup_integration(
    hass: HomeAssistant, mock_client: AsyncMock
) -> MockConfigEntry:
    """Set up the integration and return the config entry."""
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


async def test_async_setup_registers_services(hass: HomeAssistant) -> None:
    """async_setup registers all three services on the domain."""
    result = await async_setup(hass, {})
    assert result is True
    assert hass.services.has_service(DOMAIN, "enable_user")
    assert hass.services.has_service(DOMAIN, "disable_user")
    assert hass.services.has_service(DOMAIN, "update_user_pin")


async def test_enable_user_service(hass: HomeAssistant) -> None:
    """enable_user service calls hub.async_update_user_status with enabled=True."""
    mock_client = _make_mock_client()
    entry = await _setup_integration(hass, mock_client)

    await hass.services.async_call(
        DOMAIN,
        "enable_user",
        {"config_entry_id": entry.entry_id, "user_id": "user-001"},
        blocking=True,
    )

    mock_client.update_user_status.assert_called_once_with("user-001", enabled=True)


async def test_disable_user_service(hass: HomeAssistant) -> None:
    """disable_user service calls hub.async_update_user_status with enabled=False."""
    mock_client = _make_mock_client()
    entry = await _setup_integration(hass, mock_client)

    await hass.services.async_call(
        DOMAIN,
        "disable_user",
        {"config_entry_id": entry.entry_id, "user_id": "user-002"},
        blocking=True,
    )

    mock_client.update_user_status.assert_called_once_with("user-002", enabled=False)


async def test_update_user_pin_service_set(hass: HomeAssistant) -> None:
    """update_user_pin service passes the PIN to hub.async_update_user_pin."""
    mock_client = _make_mock_client()
    entry = await _setup_integration(hass, mock_client)

    await hass.services.async_call(
        DOMAIN,
        "update_user_pin",
        {"config_entry_id": entry.entry_id, "user_id": "user-001", "pin": "1234"},
        blocking=True,
    )

    mock_client.update_user_pin.assert_called_once_with("user-001", "1234")


async def test_update_user_pin_service_no_pin(hass: HomeAssistant) -> None:
    """update_user_pin without pin field passes None to hub.async_update_user_pin."""
    mock_client = _make_mock_client()
    entry = await _setup_integration(hass, mock_client)

    await hass.services.async_call(
        DOMAIN,
        "update_user_pin",
        {"config_entry_id": entry.entry_id, "user_id": "user-001"},
        blocking=True,
    )

    mock_client.update_user_pin.assert_called_once_with("user-001", None)


async def test_service_invalid_config_entry(hass: HomeAssistant) -> None:
    """Services raise ServiceValidationError for unknown config_entry_id."""
    mock_client = _make_mock_client()
    await _setup_integration(hass, mock_client)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "enable_user",
            {"config_entry_id": "nonexistent-entry-id", "user_id": "user-001"},
            blocking=True,
        )

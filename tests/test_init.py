"""Tests for the integration setup (__init__.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_access import (
    UnifiAccessData,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.unifi_access.const import DOMAIN

from .conftest import MOCK_CONFIG, SAMPLE_DOORS, SAMPLE_EMERGENCY_STATUS, SAMPLE_LOCK_RULE_STATUS


@pytest.fixture
def mock_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and add a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="192.168.1.1",
        title="Unifi Access Doors",
    )
    entry.add_to_hass(hass)
    return entry


def _make_mock_client() -> AsyncMock:
    """Create a fully mocked API client."""
    client = AsyncMock()
    client.get_doors = AsyncMock(return_value=SAMPLE_DOORS)
    client.get_door_lock_rule = AsyncMock(return_value=SAMPLE_LOCK_RULE_STATUS)
    client.get_emergency_status = AsyncMock(return_value=SAMPLE_EMERGENCY_STATUS)
    client.start_websocket = MagicMock()
    client.close = AsyncMock()
    return client


async def test_setup_entry(hass: HomeAssistant, mock_entry: MockConfigEntry) -> None:
    """Test successful setup of a config entry."""
    mock_client = _make_mock_client()

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
        result = await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    assert result is True
    assert isinstance(mock_entry.runtime_data, UnifiAccessData)
    assert mock_entry.runtime_data.hub is not None
    assert mock_entry.runtime_data.coordinator is not None
    assert mock_entry.runtime_data.emergency_coordinator is not None

    # WebSocket should be started for non-polling mode
    mock_client.start_websocket.assert_called_once()


async def test_setup_entry_polling(
    hass: HomeAssistant,
) -> None:
    """Test setup with polling mode (no websocket)."""
    mock_client = _make_mock_client()

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**MOCK_CONFIG, "use_polling": True},
        unique_id="192.168.1.2",
        title="Unifi Access Doors (Polling)",
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
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is True
    # WebSocket should NOT be started in polling mode
    mock_client.start_websocket.assert_not_called()


async def test_unload_entry(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test unloading a config entry."""
    mock_client = _make_mock_client()

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
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.async_unload(mock_entry.entry_id)
        await hass.async_block_till_done()

    assert result is True
    mock_client.close.assert_called_once()

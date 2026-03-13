"""Tests for diagnostics.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_access.const import DOMAIN
from custom_components.unifi_access.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import (
    MOCK_CONFIG,
    SAMPLE_DOORS,
    SAMPLE_EMERGENCY_STATUS,
    SAMPLE_LOCK_RULE_STATUS,
)


def _make_mock_client() -> AsyncMock:
    """Create a fully mocked API client."""
    client = AsyncMock()
    client.authenticate = AsyncMock()
    client.get_doors = AsyncMock(return_value=SAMPLE_DOORS)
    client.get_door_lock_rule = AsyncMock(return_value=SAMPLE_LOCK_RULE_STATUS)
    client.get_emergency_status = AsyncMock(return_value=SAMPLE_EMERGENCY_STATUS)
    client.start_websocket = MagicMock()
    client.close = AsyncMock()
    return client


async def test_diagnostics(hass: HomeAssistant) -> None:
    """Test diagnostics output contains expected keys and redacts secrets."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="192.168.1.1",
        title="Unifi Access Doors",
    )
    entry.add_to_hass(hass)

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
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)

    # API token should be redacted
    assert result["config_entry"]["api_token"] == "**REDACTED**"
    assert result["config_entry"]["host"] == "192.168.1.1"

    # Hub state
    assert result["use_polling"] is False
    assert result["supports_door_lock_rules"] is True
    assert result["evacuation"] is False
    assert result["lockdown"] is False

    # Doors
    assert "door-001" in result["doors"]
    assert "door-002" in result["doors"]
    assert result["doors"]["door-001"]["name"] == "Front Door"

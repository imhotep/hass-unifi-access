"""Tests for the options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_access.const import (
    CONF_DOUBLE_DRIVEWAY_ELIGIBLE_DOORS,
    DOMAIN,
)

from .conftest import MOCK_CONFIG


async def test_options_flow_reloads_entry(
    hass: HomeAssistant, mock_api_client: AsyncMock
) -> None:
    """Saving options reloads the entry (OptionsFlowWithReload)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id="192.168.1.1",
        title="Unifi Access Doors",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.unifi_access.UnifiAccessApiClient",
            return_value=mock_api_client,
        ),
        patch(
            "custom_components.unifi_access.async_get_clientsession",
            return_value=AsyncMock(),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        with patch.object(
            hass.config_entries,
            "async_reload",
            wraps=hass.config_entries.async_reload,
        ) as reload_entry:
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {CONF_DOUBLE_DRIVEWAY_ELIGIBLE_DOORS: ["door-001"]},
            )
            await hass.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options[CONF_DOUBLE_DRIVEWAY_ELIGIBLE_DOORS] == ["door-001"]
        reload_entry.assert_called_once_with(entry.entry_id)

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

"""Tests for config_flow.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unifi_access_api import ApiAuthError, ApiConnectionError, ApiSSLError

from custom_components.unifi_access.const import DOMAIN

from .conftest import MOCK_CONFIG


async def test_user_flow_success(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test a successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_CONFIG,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Unifi Access Doors"
    assert result["data"] == MOCK_CONFIG


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test config flow when connection fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(
            side_effect=ApiConnectionError("fail")
        )
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_CONFIG,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_invalid_api_key(hass: HomeAssistant) -> None:
    """Test config flow with invalid API key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(side_effect=ApiAuthError("bad key"))
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_CONFIG,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_api_key"}


async def test_user_flow_ssl_error(hass: HomeAssistant) -> None:
    """Test config flow with SSL verification failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(side_effect=ApiSSLError("ssl fail"))
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_CONFIG,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "ssl_error"}


async def test_user_flow_unknown_error(hass: HomeAssistant) -> None:
    """Test config flow with an unexpected exception."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(side_effect=RuntimeError("boom"))
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_CONFIG,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry, mock_setup_entry
) -> None:
    """Test aborting if the host is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_CONFIG,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# Reauth flow
# ---------------------------------------------------------------------------


async def test_reauth_flow_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_setup_entry
) -> None:
    """Test successful re-authentication flow."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_token": "new-token"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data["api_token"] == "new-token"


async def test_reauth_flow_invalid_key(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test re-authentication with invalid API key."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(side_effect=ApiAuthError("bad key"))
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_token": "bad-token"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_api_key"}


# ---------------------------------------------------------------------------
# Reconfigure flow
# ---------------------------------------------------------------------------


async def test_reconfigure_flow_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_setup_entry
) -> None:
    """Test successful reconfigure flow."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new_data = {
        "host": "192.168.1.99",
        "api_token": "new-token",
        "verify_ssl": True,
        "use_polling": True,
    }

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=new_data,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data["host"] == "192.168.1.99"
    assert mock_config_entry.data["use_polling"] is True


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test reconfigure when connection fails."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.unifi_access.config_flow.UnifiAccessApiClient"
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(side_effect=ApiConnectionError("fail"))
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_CONFIG,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

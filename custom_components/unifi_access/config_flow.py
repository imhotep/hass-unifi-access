"""Config flow for Unifi Access integration."""
from __future__ import annotations

import logging
from typing import Any

from .api import UnifiAccessApi

from .const import DOMAIN

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("api_token"): str,
        vol.Required("verify_ssl"): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    api = UnifiAccessApi(data["host"], data["verify_ssl"])

    auth_response = await hass.async_add_executor_job(
        api.authenticate, data["api_token"]
    )

    match auth_response:
        case "api_error":
            raise CannotConnect
        case "api_auth_error":
            raise InvalidApiKey
        case "ssl_error":
            raise SSLVerificationError
        case "ok":
            _LOGGER.info("Unifi Access API authorized")

    # Return info that you want to store in the config entry.
    return {"title": "Unifi Access Doors"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Unifi Access."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidApiKey:
                errors["base"] = "invalid_api_key"
            except SSLVerificationError:
                errors["base"] = "ssl_error"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class SSLVerificationError(HomeAssistantError):
    """Error to indicate there is failed SSL certificate verification."""


class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is invalid auth."""

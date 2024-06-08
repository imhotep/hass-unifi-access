"""Config flow for Unifi Access integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .hub import UnifiAccessHub

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("api_token"): str,
        vol.Required("verify_ssl"): bool,
        vol.Required("use_polling"): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    api = UnifiAccessHub(data["host"], data["verify_ssl"], data["use_polling"])

    auth_response = await hass.async_add_executor_job(
        api.authenticate, data["api_token"]
    )

    match auth_response:
        case "cannot_connect":
            raise CannotConnect
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


class UnifiAccessConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Unifi Access."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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

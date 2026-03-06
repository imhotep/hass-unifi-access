"""Config flow for Unifi Access integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from unifi_access_api import (
    ApiAuthError,
    ApiConnectionError,
    ApiSSLError,
    UnifiAccessApiClient,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("api_token"): str,
        vol.Required("verify_ssl", default=False): bool,
        vol.Required("use_polling", default=False): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass, verify_ssl=data["verify_ssl"])
    client = UnifiAccessApiClient(
        host=data["host"],
        api_token=data["api_token"],
        session=session,
        verify_ssl=data["verify_ssl"],
    )
    try:
        await client.authenticate()
    except ApiAuthError as err:
        raise InvalidApiKey from err
    except ApiSSLError as err:
        raise SSLVerificationError from err
    except ApiConnectionError as err:
        raise CannotConnect from err

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
            await self.async_set_unique_id(user_input["host"])
            self._abort_if_unique_id_configured()
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidApiKey:
                errors["base"] = "invalid_api_key"
            except SSLVerificationError:
                errors["base"] = "ssl_error"
            except Exception:
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


# Backwards compatible alias used by the tests
InvalidAuth = InvalidApiKey

"""Config flow for Unifi Access integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import ssl as ssl_util
from unifi_access_api import (
    ApiAuthError,
    ApiConnectionError,
    ApiSSLError,
    UnifiAccessApiClient,
)
import voluptuous as vol

from .const import CONF_DOUBLE_DRIVEWAY_ELIGIBLE_DOORS, DOMAIN, HUB_TYPE_UGT

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
    ssl_context = ssl_util.client_context() if data["verify_ssl"] else None
    client = UnifiAccessApiClient(
        host=data["host"],
        api_token=data["api_token"],
        session=session,
        verify_ssl=data["verify_ssl"],
        ssl_context=ssl_context,
    )
    try:
        await client.authenticate()
    except ApiAuthError as err:
        raise InvalidApiKeyError from err
    except ApiSSLError as err:
        raise SSLVerificationError from err
    except ApiConnectionError as err:
        raise CannotConnectError from err

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
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except InvalidApiKeyError:
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

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when the API token is invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication with a new API token."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            data = {**reauth_entry.data, "api_token": user_input["api_token"]}
            try:
                await validate_input(self.hass, data)
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except InvalidApiKeyError:
                errors["base"] = "invalid_api_key"
            except SSLVerificationError:
                errors["base"] = "ssl_error"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry, data=data
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required("api_token"): str}
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            data = {**reconfigure_entry.data, **user_input}
            try:
                await validate_input(self.hass, data)
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except InvalidApiKeyError:
                errors["base"] = "invalid_api_key"
            except SSLVerificationError:
                errors["base"] = "ssl_error"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reconfigure_entry, data=data
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "host", default=reconfigure_entry.data["host"]
                    ): str,
                    vol.Required(
                        "api_token", default=reconfigure_entry.data["api_token"]
                    ): str,
                    vol.Required(
                        "verify_ssl",
                        default=reconfigure_entry.data["verify_ssl"],
                    ): bool,
                    vol.Required(
                        "use_polling",
                        default=reconfigure_entry.data["use_polling"],
                    ): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return UnifiAccessOptionsFlow()


class UnifiAccessOptionsFlow(OptionsFlow):
    """Options flow for Unifi Access.

    Currently used only to declare which UGT door(s) are actually wired
    dual-relay (double-driveway) — see CONF_DOUBLE_DRIVEWAY_ELIGIBLE_DOORS
    in const.py for why this can't be detected from the API.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the installer declare double-driveway-eligible UGT doors."""
        data = getattr(self.config_entry, "runtime_data", None)
        if data is None:
            return self.async_abort(reason="integration_not_ready")
        ugt_doors = {
            door_id: door_state.name
            for door_id, door_state in data.coordinator.data.items()
            if door_state.hub_type == HUB_TYPE_UGT
        }

        if not ugt_doors:
            return self.async_abort(reason="no_ugt_doors")

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_DOUBLE_DRIVEWAY_ELIGIBLE_DOORS, []
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DOUBLE_DRIVEWAY_ELIGIBLE_DOORS, default=current
                    ): cv.multi_select(ugt_doors)
                }
            ),
        )


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class SSLVerificationError(HomeAssistantError):
    """Error to indicate there is failed SSL certificate verification."""


class InvalidApiKeyError(HomeAssistantError):
    """Error to indicate there is invalid auth."""

"""Config flow for Cosmos integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api_client import CosmosClient
from .config import load_config_from_dict
from .const import CONF_MANDANT, CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .exceptions import AuthenticationError, CosmosError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_MANDANT): str,
    }
)

# Options schema for update interval
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional("update_interval", default=5): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=60)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Args:
        hass: Home Assistant instance
        data: User input data with username, password, and mandant

    Returns:
        Dict with title for the config entry

    Raises:
        InvalidAuthError: If authentication fails
        CannotConnectError: If connection fails
    """
    # Parse config at boundary (Law of Parse Don't Validate)
    config = load_config_from_dict(data)

    try:
        async with CosmosClient(config) as client:
            await client.login()
    except AuthenticationError:
        raise InvalidAuthError from None
    except CosmosError as err:
        raise CannotConnectError(str(err)) from err
    except Exception as err:
        _LOGGER.exception("Unexpected exception during validation")
        raise CannotConnectError(str(err)) from err

    return {"title": f"Cosmos ({data[CONF_USERNAME]})"}


class CosmosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cosmos."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict[str, str] = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnectError:
            errors["base"] = "cannot_connect"
        except InvalidAuthError:
            errors["base"] = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CosmosOptionsFlow:
        """Get the options flow for this handler."""
        return CosmosOptionsFlow()


class CosmosOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Cosmos."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=self._get_options_schema(),
            )

        return self.async_create_entry(title="", data=user_input)

    def _get_options_schema(self) -> vol.Schema:
        """Return options schema with current values."""
        current_interval = self.config_entry.options.get("update_interval", 5)
        return vol.Schema(
            {
                vol.Optional("update_interval", default=current_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=60)
                ),
            }
        )


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuthError(HomeAssistantError):
    """Error to indicate there is invalid auth."""

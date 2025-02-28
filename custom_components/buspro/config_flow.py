import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_TIME_BROADCAST

from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
)

_LOGGER = logging.getLogger(__name__)

# Konstanty pro formulář
FORM_DESCRIPTION_PLACEHOLDERS = {
    "time_broadcast_description": "When enabled, Home Assistant will act as a time source for HDL Buspro devices by broadcasting current time every minute"
}

def _get_form_schema(defaults=None):
    """Get schema with default values."""
    if defaults is None:
        defaults = {}
    
    return vol.Schema({
        vol.Required(
            CONF_BROADCAST_ADDRESS, 
            default=defaults.get(CONF_BROADCAST_ADDRESS, "192.168.10.255")
        ): cv.string,
        vol.Required(
            CONF_BROADCAST_PORT, 
            default=defaults.get(CONF_BROADCAST_PORT, 6000)
        ): cv.port,
        vol.Optional(
            CONF_TIME_BROADCAST, 
            default=defaults.get(CONF_TIME_BROADCAST, True)
        ): bool
    })

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:                
                if CONF_TIME_BROADCAST not in user_input:
                    user_input[CONF_TIME_BROADCAST] = True
                return self.async_create_entry(title="Buspro", data=user_input)
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=_get_form_schema(),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BusproOptionsFlowHandler(config_entry)

class BusproOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input
            )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_get_form_schema(self.config_entry.data)
        )
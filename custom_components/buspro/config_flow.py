import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries

from .const import (
    DOMAIN,
)

from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
)
_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            try:
                return self.async_create_entry(title="Buspro", data=user_input)
                    
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",

            data_schema=vol.Schema({
            	vol.Required(CONF_BROADCAST_ADDRESS, default="192.168.10.255"): cv.string,
            	vol.Required(CONF_BROADCAST_PORT, default=6000): cv.port
            	#vol.Required(CONF_BROADCAST_ADDRESS): cv.string,
            	#vol.Required(CONF_BROADCAST_PORT): cv.port
            }),
            errors=errors
        )

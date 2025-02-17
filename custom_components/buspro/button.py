"""Support for HDL Buspro buttons."""
import logging
import voluptuous as vol
from homeassistant.components.button import ButtonEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_DEVICES
import homeassistant.helpers.config_validation as cv

from custom_components.buspro import DATA_BUSPRO
from .pybuspro.devices import Button


_LOGGER = logging.getLogger(__name__)

CONF_PAYLOAD = "payload"
CONF_VALUE = "value"
DEFAULT_VALUE = True

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_VALUE, default=DEFAULT_VALUE): cv.boolean,    
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): {cv.string: DEVICE_SCHEMA},
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Buspro button devices."""
    hdl = hass.data[DATA_BUSPRO].hdl
    devices = []

    for address, device_config in config[CONF_DEVICES].items():
        name = device_config[CONF_NAME]
        value = device_config[CONF_VALUE]  # Získáme hodnotu pro key_status

        address2 = address.split('.')
        device_address = (int(address2[0]), int(address2[1]))
        button_number = int(address2[2])

        _LOGGER.debug(f"Adding button '{name}' with address {device_address}, button number {button_number}, value {value}")
        
        button = Button(hdl, device_address, button_number, name)
        devices.append(BusproButton(hass, button, value))

    async_add_entities(devices)

class BusproButton(ButtonEntity):
    """Representation of a Buspro button."""

    def __init__(self, hass, device, value):
        self._hass = hass
        self._device = device
        self._value = value
        
    @property
    def name(self):
        """Return the display name of this button."""
        return self._device.name

    @property
    def unique_id(self):
        """Return unique ID."""
        return self._device.device_identifier

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._device.press(self._value)
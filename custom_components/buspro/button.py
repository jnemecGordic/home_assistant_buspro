"""Support for HDL Buspro buttons."""
import asyncio
import logging
import voluptuous as vol
from homeassistant.components.button import ButtonEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_DEVICES
import homeassistant.helpers.config_validation as cv

from custom_components.buspro.helpers import wait_for_buspro
from custom_components.buspro.pybuspro.devices.panel import Panel
from .pybuspro.devices import Button


_LOGGER = logging.getLogger(__name__)

def validate_button_address(value):
    """Validace formátu adresy tlačítka."""
    try:
        parts = value.split('.')
        if len(parts) != 4:
            raise vol.Invalid("Address must be in format: subnet.device.button.on|off")
        
        subnet = int(parts[0])
        device = int(parts[1])
        button = int(parts[2])
        state = parts[3].lower()
        
        if not (1 <= subnet <= 255 and 1 <= device <= 255 and 1 <= button <= 255):
            raise vol.Invalid("Subnet, device and button numbers must be between 1 and 255")
            
        if state not in ('on', 'off'):
            raise vol.Invalid("State must be 'on' or 'off'")
            
        return value
    except (ValueError, IndexError):
        raise vol.Invalid("Invalid address format")

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): {validate_button_address: DEVICE_SCHEMA},
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Buspro button devices."""
    if not await wait_for_buspro(hass):
        return False
    devices = []

    for address, device_config in config[CONF_DEVICES].items():
        name = device_config[CONF_NAME]        
        
        address_parts = address.split('.')
        device_address = (int(address_parts[0]), int(address_parts[1]))
        button_number = int(address_parts[2])
        value = address_parts[3].lower() == "on"

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Adding button '{name}' with address {device_address}, button number {button_number}, value {value}")
        
        
        panel = Panel(hass, device_address, name)
        button = Button(panel, button_number, name)
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
        """Return unique ID for this button."""
        subnet, device = self._device._panel._device_address
        button = getattr(self._device, "_button_number", "N")
        return f"{subnet}-{device}-{button}-{self._value}-button"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._device.press(self._value)
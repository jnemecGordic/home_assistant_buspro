"""Support for HDL Buspro buttons."""
import asyncio
import logging
import voluptuous as vol
from homeassistant.components.button import ButtonEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_DEVICES
import homeassistant.helpers.config_validation as cv

from custom_components.buspro import DATA_BUSPRO
from custom_components.buspro.helpers import wait_for_buspro
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
    if not await wait_for_buspro(hass, DATA_BUSPRO):
        return False
    hdl = hass.data[DATA_BUSPRO].hdl
    devices = []

    for address, device_config in config[CONF_DEVICES].items():
        name = device_config[CONF_NAME]
        
        # Zpracování adresy ve formátu "subnet.device.button.state"
        address_parts = address.split('.')
        if len(address_parts) != 4:
            _LOGGER.error(f"Invalid address format for button '{name}': {address}. Use format: subnet.device.button.on|off")
            continue
            
        device_address = (int(address_parts[0]), int(address_parts[1]))
        button_number = int(address_parts[2])
        value = address_parts[3].lower() == "on"  # "on" = True, "off" = False

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
        return f"{self._device.device_identifier}-{self._value}"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._device.press(self._value)
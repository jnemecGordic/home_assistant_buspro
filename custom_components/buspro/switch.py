"""
This component provides switch support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.switch import SwitchEntity, PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_DEVICES, CONF_SCAN_INTERVAL)
from homeassistant.core import callback

from ..buspro import DATA_BUSPRO

_LOGGER = logging.getLogger(__name__)

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=0): cv.positive_int,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): {cv.string: DEVICE_SCHEMA},
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Buspro switch devices."""
    from .pybuspro.devices import Switch

    hdl = hass.data[DATA_BUSPRO].hdl
    devices = []

    for address, device_config in config[CONF_DEVICES].items():
        name = device_config[CONF_NAME]
        scan_interval = device_config[CONF_SCAN_INTERVAL]
        address2 = address.split('.')
        device_address = (int(address2[0]), int(address2[1]))
        channel_number = int(address2[2])
        _LOGGER.debug("Adding switch '{}' with address {} and channel number {} scan interval {}".format(name, device_address, channel_number,scan_interval))

        switch = Switch(hdl, device_address, channel_number, name)

        devices.append(BusproSwitch(hass, switch, scan_interval))

    async_add_entities(devices)



# noinspection PyAbstractClass
class BusproSwitch(SwitchEntity):
    def __init__(self, hass, device, scan_interval):
        self._scan_interval = 0
        self._hass = hass
        self._device = device
        self._scan_interval = scan_interval
        self.async_register_callbacks()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        _LOGGER.debug("Added switch '{}' scan interval {}".format(self._device.name, self.scan_interval))
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)



    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        # noinspection PyUnusedLocal
        async def after_update_callback(device):
            """Call after device was updated."""
            self.async_write_ha_state()

        self._device.register_device_updated_cb(after_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro."""
        return False

    async def async_update(self):
        await self._device.read_status()

    @property
    def name(self):
        """Return the display name of this light."""
        return self._device.name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._hass.data[DATA_BUSPRO].connected

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.is_on

    @property
    def scan_interval(self):
        """Return the scan interval of the switch."""
        return self._scan_interval

    async def async_turn_on(self, **kwargs):
        """Instruct the switch to turn on."""
        await self._device.set_on()

    async def async_turn_off(self, **kwargs):
        """Instruct the switch to turn off."""
        await self._device.set_off()

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._device.device_identifier

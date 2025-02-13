"""
This component provides binary sensor support for Buspro.
"""

import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorEntity
from homeassistant.const import CONF_NAME, CONF_DEVICES, CONF_ADDRESS, CONF_TYPE, CONF_DEVICE_CLASS, CONF_SCAN_INTERVAL
from homeassistant.core import callback

from custom_components.buspro.pybuspro.devices.sensor import SensorType
from ..buspro import DATA_BUSPRO

_LOGGER = logging.getLogger(__name__)

DEFAULT_CONF_DEVICE_CLASS = "None"
DEFAULT_CONF_SCAN_INTERVAL = 0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_TYPE): cv.string,  # Expecting string from config
                vol.Optional(CONF_DEVICE_CLASS, default=DEFAULT_CONF_DEVICE_CLASS): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_CONF_SCAN_INTERVAL): cv.positive_int,
            })
        ])
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro binary sensor devices."""
    from .pybuspro.devices import Sensor, SensorType, DeviceClass  # Import enums

    hdl = hass.data[DATA_BUSPRO].hdl
    devices = []

    for device_config in config[CONF_DEVICES]:
        address = device_config[CONF_ADDRESS]
        name = device_config[CONF_NAME]
        sensor_type_str = device_config[CONF_TYPE]  # Get sensor type as string
        device_class_str = device_config[CONF_DEVICE_CLASS]

        # Convert string representations to enums
        try:
            sensor_type = SensorType(sensor_type_str)
        except ValueError:
            _LOGGER.error(f"Invalid sensor type: {sensor_type_str}")
            continue

        try:
            device_class = DeviceClass(device_class_str) if device_class_str != "None" else None
        except ValueError:
            _LOGGER.error(f"Invalid device class: {device_class_str}")
            continue

        scan_interval = device_config[CONF_SCAN_INTERVAL]

        address2 = address.split('.')
        device_address = (int(address2[0]), int(address2[1]))

        _LOGGER.debug(f"Adding binary sensor '{name}' with address {device_address}, sensor type '{sensor_type}'")

        sensor = Sensor(hdl, device_address, device_class=device_class, sensor_type=sensor_type.value, name=name)  # Pass enum value

        devices.append(BusproBinarySensor(hass, sensor, sensor_type, scan_interval))

    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproBinarySensor(BinarySensorEntity):
    """Representation of a Buspro binary sensor."""

    def __init__(self, hass, device, sensor_type, scan_interval):
        """Initialize the Buspro binary sensor."""
        self._hass = hass
        self._device = device
        self._sensor_type = sensor_type
        self._scan_interval = scan_interval
        self._is_on = False  # Initial state
        self.async_register_callbacks()

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"Added binary sensor '{self._device.name}' scan interval {self.scan_interval}")
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            self.async_write_ha_state()

        self._device.register_device_updated_cb(after_update_callback)

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        if self._sensor_type == SensorType.MOTION:
            return self._device.movement
        elif self._sensor_type == SensorType.DRY_CONTACT_1:
            return self._device.dry_contact_1_is_on
        elif self._sensor_type == SensorType.DRY_CONTACT_2:
            return self._device.dry_contact_2_is_on
        elif self._sensor_type == SensorType.UNIVERSAL_SWITCH:
            return self._device.universal_switch_is_on
        elif self._sensor_type == SensorType.SINGLE_CHANNEL:
            return self._device.single_channel_is_on
        return self._device.switch_status

    @property
    def should_poll(self):
        """No polling needed within Buspro unless explicitly set."""
        return False

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._device.name

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return None  # You can set a device class if appropriate

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self._device.device_identifier}-{self._sensor_type.value}"

    @property
    def scan_interval(self):
        """Return the scan interval of the sensor."""
        return self._scan_interval

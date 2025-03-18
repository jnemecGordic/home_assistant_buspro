"""
This component provides sensor support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    DEVICE_CLASSES_SCHEMA,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICES,
    CONF_ADDRESS,
    CONF_TYPE,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_DEVICE,
    CONF_SCAN_INTERVAL,
    CONF_DEVICE_CLASS,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from custom_components.buspro.helpers import wait_for_buspro
from .pybuspro.devices.sensor import SensorType, DeviceFamily
from .pybuspro.helpers.enums import validate_device_family
from ..buspro import DATA_BUSPRO

DEFAULT_CONF_UNIT_OF_MEASUREMENT = ""
DEFAULT_CONF_DEVICE = "None"
DEFAULT_CONF_OFFSET = 0
CONF_OFFSET = "offset"
DEFAULT_CONF_SCAN_INTERVAL = 0

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    SensorType.ILLUMINANCE.value,
    SensorType.TEMPERATURE.value,
    SensorType.HUMIDITY.value
}


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_TYPE): vol.In(SENSOR_TYPES),
                vol.Optional(CONF_UNIT_OF_MEASUREMENT, default=DEFAULT_CONF_UNIT_OF_MEASUREMENT): cv.string,
                vol.Optional(CONF_DEVICE, default=DEFAULT_CONF_DEVICE): vol.All(cv.string, validate_device_family),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_CONF_SCAN_INTERVAL): cv.positive_int,                
                vol.Optional(CONF_OFFSET, default=DEFAULT_CONF_OFFSET): vol.Coerce(int),
                vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
            })
        ])
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro sensor devices."""
    # noinspection PyUnresolvedReferences
    from .pybuspro.devices import Sensor

    if not await wait_for_buspro(hass):
        return False    
    
    devices = []

    for device_config in config[CONF_DEVICES]:
        address = device_config[CONF_ADDRESS]
        name = device_config[CONF_NAME]
        sensor_type_str = device_config[CONF_TYPE]
        device_family_str = device_config[CONF_DEVICE]
        offset = device_config[CONF_OFFSET]
        scan_interval = device_config[CONF_SCAN_INTERVAL]
        device_class = device_config.get(CONF_DEVICE_CLASS)

        try:
            sensor_type = SensorType(sensor_type_str)
        except ValueError:
            _LOGGER.error(f"Invalid sensor type: {sensor_type_str}")
            continue

        try:
            device_family = DeviceFamily(device_family_str) if device_family_str != "None" else None
        except ValueError:
            _LOGGER.error(f"Invalid device class: {device_family_str}")
            continue

        address2 = address.split('.')        
        device_address = (int(address2[0]), int(address2[1]))        
        channel_number = None

        if SensorType.TEMPERATURE == sensor_type:
            if DeviceFamily.PANEL == device_family and len(address2) == 2:
                channel_number = 1
            if len(address2) > 2:
                channel_number = int(address2[2])

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Adding sensor '{name}' with address {device_address}, sensor type '{sensor_type}'")
        sensor = Sensor(hass, device_address, device_family=device_family, sensor_type=sensor_type, name=name, channel_number=channel_number)
        devices.append(BusproSensor(hass, sensor, sensor_type, scan_interval, offset, device_class))


    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproSensor(Entity):
    """Representation of a Buspro sensor."""

    def __init__(self, hass, device, sensor_type, scan_interval, offset, device_class=None):
        self._hass = hass
        self._device = device
        self._sensor_type = sensor_type        
        self._offset = offset
        self._temperature = None
        self._brightness = None
        self._humidity = None
        self._scan_interval = scan_interval
        self._custom_device_class = device_class
        self.async_register_callbacks()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Added sensor '{}' scan interval {}".format(self._device.name, self.scan_interval))
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            if self._hass is not None:
                self._temperature = self._device.temperature
                self._brightness = self._device.brightness
                self._humidity = self._device.humidity                
                self.async_write_ha_state()
                await self._hass.data[DATA_BUSPRO].scheduler.device_updated(self.entity_id)

        self._device.register_device_updated_cb(after_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro unless explicitly set."""
        return False

    async def async_update(self):
        await self._device.read_sensor_status()

    @property
    def name(self):
        """Return the display name of this light."""
        return self._device.name

    @property
    def available(self):
        """Return True if entity is available."""
        connected = self._hass.data[DATA_BUSPRO].connected

        if self._sensor_type == SensorType.TEMPERATURE:
            return connected and self._current_temperature is not None
        if self._sensor_type == SensorType.HUMIDITY:
            return connected and self._humidity is not None
        if self._sensor_type == SensorType.ILLUMINANCE:
            return connected and self._brightness is not None

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._sensor_type == SensorType.TEMPERATURE:
            return self._current_temperature
        if self._sensor_type == SensorType.ILLUMINANCE:
            return self._brightness
        if self._sensor_type == SensorType.HUMIDITY:
            return self._humidity            

    @property
    def _current_temperature(self):
        if self._temperature is None:
            return None
        if self._offset is not None:
            return self._temperature + int(self._offset)
        return self._temperature
        

    @property
    def device_class(self):
        """Return the class of this sensor."""
        if self._custom_device_class is not None:
            return self._custom_device_class            
        if self._sensor_type == SensorType.TEMPERATURE:
            return "temperature"
        if self._sensor_type == SensorType.ILLUMINANCE:
            return "illuminance"
        if self._sensor_type == SensorType.HUMIDITY:
            return "humidity"
        return None

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        if self._sensor_type == SensorType.TEMPERATURE:
            return "°C"
        if self._sensor_type == SensorType.ILLUMINANCE:
            return "lux"
        if self._sensor_type == SensorType.HUMIDITY:
            return "%"
        return ""

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = {'state_class': "measurement"}
        return attributes

    @property
    def unique_id(self):
        """Return unique ID for this sensor."""
        subnet, device = self._device._device_address
        
        if self._sensor_type == SensorType.TEMPERATURE:            
            channel = getattr(self._device, "_channel_number", "N")            
            if DeviceFamily.PANEL == self._device._device_family and channel == 1:
                channel = "N"
        elif self._sensor_type == SensorType.DRY_CONTACT:
            channel = getattr(self._device, "_switch_number", "N")
        elif self._sensor_type == SensorType.UNIVERSAL_SWITCH:
            channel = getattr(self._device, "_universal_switch_number", "N")
        elif self._sensor_type == SensorType.SINGLE_CHANNEL:
            channel = getattr(self._device, "_channel_number", "N") 
        else:
            channel = "N"
        
        return f"{subnet}-{device}-{channel}-sensor-{self._sensor_type.value}"

    @property
    def scan_interval(self):
        """Return the scan interval of the sensor."""
        return self._scan_interval
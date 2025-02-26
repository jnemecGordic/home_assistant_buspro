"""Support for HDL Buspro alarm control panel."""
import logging
import re
import voluptuous as vol

from homeassistant.components.alarm_control_panel import (
    PLATFORM_SCHEMA,
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelState,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_ADDRESS,
    CONF_DEVICES,
    CONF_SCAN_INTERVAL,
)
import homeassistant.helpers.config_validation as cv

from custom_components.buspro import DATA_BUSPRO
from custom_components.buspro.helpers import wait_for_buspro
from .pybuspro.devices.security import Security, SecurityStatus

_LOGGER = logging.getLogger(__name__)

def validate_address(value: str) -> str:
    """Validate Buspro device address.
    
    Expected format: subnet.device.area where:
    - subnet: 0-255
    - device: 0-255
    - area: 1-8
    """
    pattern = r'^\d+\.\d+\.\d+$'
    if not re.match(pattern, value):
        raise vol.Invalid(
            f"Invalid address format: {value}. Expected format: 'subnet.device.area'"
        )
    parts = [int(x) for x in value.split(".")]
    if not (0 <= parts[0] <= 255 and 0 <= parts[1] <= 255):
        raise vol.Invalid(
            f"Invalid address values: {value}. Subnet and device must be 0-255"
        )
    if not (1 <= parts[2] <= 8):
        raise vol.Invalid(
            f"Invalid area value: {parts[2]}. Area must be 1-8"
        )
    return value

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        vol.Schema({
            vol.Required(CONF_ADDRESS): validate_address,
            vol.Required(CONF_NAME): cv.string,
            vol.Optional(CONF_SCAN_INTERVAL, default=0): cv.positive_int,
        })
    ])
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the HDL Buspro alarm control panel devices."""
    if not await wait_for_buspro(hass, DATA_BUSPRO):
        return False

    hdl = hass.data[DATA_BUSPRO].hdl
    devices = []

    for device_config in config[CONF_DEVICES]:
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', device_config[CONF_ADDRESS])
        if not match:
            continue
            
        name = device_config[CONF_NAME]
        scan_interval = device_config.get(CONF_SCAN_INTERVAL, 0)
        subnet_id, device_id, area_id = map(int, match.groups())
        
        device = Security(hdl, (subnet_id, device_id), area_id, name)
        
        panel = HDLBusproAlarmPanel(
            hass,
            device,
            name,
            scan_interval
        )
        devices.append(panel)
        _LOGGER.debug(f"Added alarm control panel '{name}' for area {area_id} with scan interval {scan_interval}s")

    async_add_entities(devices)
    return True
    

class HDLBusproAlarmPanel(AlarmControlPanelEntity):
    """Representation of HDL Buspro Alarm Control Panel."""

    def __init__(self, hass, device, name, scan_interval=0):
        """Initialize alarm control panel entity."""
        self._name = name
        self._hass = hass
        self._device = device
        self._scan_interval = scan_interval
        self._attr_supported_features = (
            AlarmControlPanelEntityFeature.ARM_HOME |
            AlarmControlPanelEntityFeature.ARM_AWAY |
            AlarmControlPanelEntityFeature.ARM_NIGHT |
            AlarmControlPanelEntityFeature.ARM_VACATION |
            AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS |
            AlarmControlPanelEntityFeature.TRIGGER
        )
        
        self._attr_code_format = None
        self._attr_code_arm_required = False
        self._device.register_device_updated_cb(self.schedule_update_ha_state)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"Added alarm control panel '{self._device._name}'")
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)
        await self.async_update()

    @property
    def name(self):
        """Return the display name of this alarm panel."""
        return self._name

    @property
    def state(self):
        """Return the state of the alarm panel."""
        if self._device.status == SecurityStatus.DISARM:
            return AlarmControlPanelState.DISARMED
        elif self._device.status == SecurityStatus.DAY:
            return AlarmControlPanelState.ARMED_HOME
        elif self._device.status == SecurityStatus.NIGHT:
            return AlarmControlPanelState.ARMED_NIGHT
        elif self._device.status == SecurityStatus.AWAY:
            return AlarmControlPanelState.ARMED_AWAY
        elif self._device.status == SecurityStatus.VACATION:
            return AlarmControlPanelState.ARMED_VACATION
        elif self._device.status == SecurityStatus.NIGHT_WITH_GUEST:
            return AlarmControlPanelState.ARMED_CUSTOM_BYPASS


    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self._device.set_status(SecurityStatus.DISARM)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""        
        await self._device.set_status(SecurityStatus.DAY)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        await self._device.set_status(SecurityStatus.AWAY)        

    async def async_alarm_arm_night(self, code=None):
        """Send arm night command."""
        await self._device.set_status(SecurityStatus.NIGHT)

    async def async_alarm_arm_vacation(self, code=None):
        """Send arm vacation command."""
        await self._device.set_status(SecurityStatus.VACATION)

    async def async_alarm_arm_custom_bypass(self, code=None):
        """Send arm custom bypass command."""
        await self._device.set_status(SecurityStatus.NIGHT_WITH_GUEST)

    async def async_alarm_trigger(self, code=None):
        """Send alarm trigger command."""        
        await self._device.set_status(SecurityStatus.AWAY)

    async def async_update(self):
        """Update alarm panel state."""
        await self._device.read_security_status()

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return False

    @property
    def unique_id(self):
        """Return unique ID for this alarm panel."""
        return f"{self._device._device_address[0]}-{self._device._device_address[1]}-{self._device._area_id}-alarm"

    @property
    def scan_interval(self):
        """Return the scan interval for this entity."""
        return self._scan_interval
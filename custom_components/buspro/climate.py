"""
This component provides sensor support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging
from typing import Optional, List
from enum import Enum

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICES,
    CONF_ADDRESS,
    UnitOfTemperature,
    ATTR_TEMPERATURE, CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback

from custom_components.buspro.helpers import wait_for_buspro
from custom_components.buspro.pybuspro.devices.climate import Climate, ControlFloorHeatingStatus
from custom_components.buspro.pybuspro.devices.sensor import Sensor

from ..buspro import DATA_BUSPRO
from .pybuspro.helpers.enums import OnOffStatus

_LOGGER = logging.getLogger(__name__)

class PresetMode(Enum):
    """Presetové módy klimatizace."""
    NONE = "none"    # Normal
    HOME = "home"    # Day
    SLEEP = "sleep"  # Night
    AWAY = "away"    # Away

# Mapování mezi HA presety a HDL hodnoty
HA_PRESET_TO_HDL = {
    PresetMode.NONE.value: 1,
    PresetMode.HOME.value: 2,
    PresetMode.SLEEP.value: 3,
    PresetMode.AWAY.value: 4,
}

HDL_TO_HA_PRESET = {
    1: PresetMode.NONE.value,
    2: PresetMode.HOME.value,
    3: PresetMode.SLEEP.value,
    4: PresetMode.AWAY.value,
}

CONF_PRESET_MODES = "preset_modes"
CONF_RELAY_ADDRESS = "relay_address"

# Přidejte tuto třídu do souboru climate.py
class ClimateDeviceType(Enum):
    """Typ HDL Buspro climate zařízení."""
    PANEL = "panel"
    FLOOR_HEATING = "floor_heating"
    DLP = "dlp"
    AIR_CONDITIONING = "air_conditioning"

# Funkce pro validaci typu klimatického zařízení
def validate_climate_device_type(value):
    """Validate climate device type."""
    try:
        return ClimateDeviceType(value).value
    except ValueError:
        raise vol.Invalid(f"Invalid climate device type '{value}'")

# Konstanty
DEFAULT_CONF_DEVICE = "panel"  # Původní výchozí hodnota
CONF_DEVICE = "device"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(CONF_DEVICE, default=DEFAULT_CONF_DEVICE): 
                    vol.All(cv.string, validate_climate_device_type),
                vol.Optional(CONF_PRESET_MODES, default=[]): vol.All(
                    cv.ensure_list, [vol.In([mode.value for mode in PresetMode])]
                ),
                vol.Optional(CONF_RELAY_ADDRESS, default=''): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=0): cv.positive_int,
            })
        ])
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro climate devices."""
    if not await wait_for_buspro(hass):
        return False    
    devices = []

    for device_config in config[CONF_DEVICES]:
        address = device_config[CONF_ADDRESS]
        name = device_config[CONF_NAME]
        device_type_str = device_config[CONF_DEVICE]
        preset_modes = device_config[CONF_PRESET_MODES]

        try:
            device_type = ClimateDeviceType(device_type_str)
        except ValueError:
            _LOGGER.error(f"Invalid device type: {device_type_str}")
            continue

        # Rozdělení adresy na části
        address2 = address.split('.')
        
        # Kontrola formátu adresy podle typu zařízení
        if len(address2) < 2:
            _LOGGER.error(f"Invalid address format for '{name}': {address}. Expected at least subnet.device")
            continue
            
        device_address = (int(address2[0]), int(address2[1]))
        
        # Zpracování čísla kanálu
        channel_number = None
        if len(address2) > 2:
            channel_number = int(address2[2])
        elif device_type != ClimateDeviceType.DLP:
            _LOGGER.error(f"Missing channel number for '{name}' with device type '{device_type.value}'. Expected format: subnet.device.channel")
            continue

        scan_interval = device_config[CONF_SCAN_INTERVAL]

        if _LOGGER.isEnabledFor(logging.DEBUG):
            channel_info = f", channel {channel_number}" if channel_number is not None else ""
            _LOGGER.debug(f"Adding climate '{name}' with address {device_address}{channel_info}, device type '{device_type.value}'")

        climate = Climate(hass, device_address, name, device_type, channel_number)

        relay_sensor = None
        relay_address = device_config[CONF_RELAY_ADDRESS]
        if relay_address:
            relay_address2 = relay_address.split('.')
            if len(relay_address2) < 3:
                _LOGGER.error(f"Invalid relay address format for '{name}': {relay_address}. Expected subnet.device.channel")
                continue
                
            relay_device_address = (int(relay_address2[0]), int(relay_address2[1]))
            relay_channel_number = int(relay_address2[2])
            relay_sensor = Sensor(hass, relay_device_address, channel_number=relay_channel_number)

        devices.append(BusproClimate(hass, climate, preset_modes, relay_sensor, scan_interval))

    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproClimate(ClimateEntity):
    """Representation of a Buspro switch."""

    def __init__(self, hass, device, preset_modes, relay_sensor, scan_interval):
        self._hass = hass
        self._device = device
        self._scan_interval = scan_interval
        self._target_temperature = self._device.target_temperature
        self._is_on = self._device.is_on
        self._preset_modes = preset_modes
        self._mode = self._device.mode  # 1/3/4

        self._relay_sensor = relay_sensor
        self._relay_sensor_is_on = None
        if self._relay_sensor is not None:
            self._relay_sensor_is_on = self._relay_sensor.single_channel_is_on

        self._enable_turn_on_off_backwards_compatibility = False
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON

        self.async_register_callbacks()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Added climate '{}' scan interval {}".format(self._device.name, self.scan_interval))
        await self._hass.data[DATA_BUSPRO].entity_initialized(self)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)
    
    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        # noinspection PyUnusedLocal
        async def after_update_callback(device):
            """Call after device was updated."""
            self._device = device
            self._target_temperature = device.target_temperature
            self._is_on = device.is_on
            self._mode = device.mode

            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"Device '{self._device.name}', " \
                            f"IsOn: {self._is_on}, " \
                            f"Mode: {self._device.mode}, " \
                            f"TargetTemp: {self._device.target_temperature}")
            
            self.async_write_ha_state()
            await self._hass.data[DATA_BUSPRO].scheduler.device_updated(self.entity_id)

        async def after_relay_sensor_update_callback(device):
            """Call after device was updated."""
            self._relay_sensor_is_on = device.single_channel_is_on
            self.async_write_ha_state()

        self._device.register_device_updated_cb(after_update_callback)

        if self._relay_sensor is not None:
            self._relay_sensor.register_device_updated_cb(after_relay_sensor_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro."""
        return False

    async def async_update(self):
        """Default async_update method that does nothing."""
        pass

    @property
    def name(self):
        """Return the display name of this light."""
        return self._device.name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._hass.data[DATA_BUSPRO].connected

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._device.temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        target_temperature = self._target_temperature
        if target_temperature is None:
            target_temperature = self._device.target_temperature

        return target_temperature

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp.
        """
        if self._mode not in list(HDL_TO_HA_PRESET):
            return PresetMode.NONE.value
        return HDL_TO_HA_PRESET[self._mode]

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes.
        Requires SUPPORT_PRESET_MODE.
        """
        if len(self._preset_modes) == 0:
            return None

        keys = HA_PRESET_TO_HDL.keys() & self._preset_modes
        ha_preset_to_hdl_configured = {k:HA_PRESET_TO_HDL[k] for k in keys}
        return list(ha_preset_to_hdl_configured)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in list(HA_PRESET_TO_HDL):
            preset_mode = PresetMode.NONE.value
        mode = HA_PRESET_TO_HDL[preset_mode]

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Setting preset mode to '{preset_mode}' ({mode}) for device '{self._device.name}'")

        climate_control = ControlFloorHeatingStatus()
        climate_control.mode = mode

        await self._device.control_heating_status(climate_control)
        self.async_write_ha_state()

    @property
    def hvac_action(self) -> Optional[str]:
        """Return current action ie. heating, idle, off."""
        if self._is_on:
            if self._relay_sensor_is_on is None:
                return HVACAction.Heat
            else:
                if self._relay_sensor_is_on:
                    return HVACAction.HEATING
                else:
                    return HVACAction.IDLE
        else:
            return HVACAction.OFF

    @property
    def hvac_mode(self) -> Optional[str]:
        """Return current operation ie. heat, cool, idle."""
        if self._is_on:
            return HVACMode.HEAT
        else:
            return HVACMode.OFF

    @property
    def hvac_modes(self) -> Optional[List[str]]:
        """Return the list of available operation modes."""
        return [HVACMode.HEAT, HVACMode.OFF]

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set operation mode."""
        if hvac_mode == HVACMode.OFF:
            climate_control = ControlFloorHeatingStatus()
            climate_control.status = OnOffStatus.OFF.value
            await self._device.control_heating_status(climate_control)
            self.async_write_ha_state()
        elif hvac_mode == HVACMode.HEAT:
            climate_control = ControlFloorHeatingStatus()
            climate_control.status = OnOffStatus.ON.value
            await self._device.control_heating_status(climate_control)
            self.async_write_ha_state()
        else:
            _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
            return

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def scan_interval(self):
        """Return the scan interval of the climate."""
        return self._scan_interval

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        climate_control = ControlFloorHeatingStatus()
        preset = HDL_TO_HA_PRESET[self._mode]
        target_temperature = int(temperature)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Setting '{preset}' temperature to {target_temperature}")
        if preset == PresetMode.NONE.value:
            climate_control.normal_temperature = target_temperature
        elif preset == PresetMode.HOME.value:
            climate_control.day_temperature = target_temperature
        elif preset == PresetMode.SLEEP.value:
            climate_control.night_temperature = target_temperature
        elif preset == PresetMode.AWAY.value:
            climate_control.away_temperature = target_temperature
        else:
            climate_control.normal_temperature = target_temperature

        await self._device.control_heating_status(climate_control)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        attrs = {}
        
        # Přidáme atributy specifické pro Floor Heating
        if self._device.device_type == ClimateDeviceType.FLOOR_HEATING:
            # Základní teploty pro každý režim
            attrs["normal_temperature"] = self._device.normal_temperature
            attrs["day_temperature"] = self._device.day_temperature
            attrs["night_temperature"] = self._device.night_temperature 
            attrs["away_temperature"] = self._device.away_temperature
            
            # Další specifické atributy
            attrs["valve_status"] = "open" if self._device.valve_status else "closed"
            attrs["valve_pwm"] = self._device.pwd_value  # 0-100%
            attrs["timer_mode"] = "night" if self._device.timer_enabled else "day"
            attrs["watering_remaining"] = self._device.watering_time  # v minutách
            
        return attrs


    @property
    def unique_id(self):
        """Return unique ID for this climate entity."""
        subnet, device = self._device._device_address
        device_type = self._device.device_type.value if self._device.device_type else "unknown"        
        
        channel_suffix = ""
        if hasattr(self._device, "_channel_number") and self._device._channel_number is not None:
            channel_suffix = f"-{self._device._channel_number}"
            
        return f"{subnet}-{device}{channel_suffix}-{device_type}-climate"
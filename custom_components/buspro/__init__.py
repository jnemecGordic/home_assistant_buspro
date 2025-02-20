"""
Support for Buspro devices.

For more details about this component, please refer to the documentation at
https://home-assistant.io/...
"""
import asyncio
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_NAME,
)
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .pybuspro.buspro import Buspro
from custom_components.buspro.scheduler import Scheduler

_LOGGER = logging.getLogger(__name__)

DATA_BUSPRO = "buspro"
DEPENDENCIES = []
DEFAULT_BROADCAST_ADDRESS = "192.168.10.255"
DEFAULT_BROADCAST_PORT = 6000


DEFAULT_CONF_NAME = ""

DEFAULT_SCENE_NAME = "BUSPRO SCENE"
DEFAULT_SEND_MESSAGE_NAME = "BUSPRO MESSAGE"

SERVICE_BUSPRO_SEND_MESSAGE = "send_message"
SERVICE_BUSPRO_ACTIVATE_SCENE = "activate_scene"
SERVICE_BUSPRO_UNIVERSAL_SWITCH = "set_universal_switch"

SERVICE_BUSPRO_ATTR_OPERATE_CODE = "operate_code"
SERVICE_BUSPRO_ATTR_ADDRESS = "address"
SERVICE_BUSPRO_ATTR_PAYLOAD = "payload"
SERVICE_BUSPRO_ATTR_SCENE_ADDRESS = "scene_address"
SERVICE_BUSPRO_ATTR_SWITCH_NUMBER = "switch_number"
SERVICE_BUSPRO_ATTR_STATUS = "status"

"""{ "address": [1,74], "scene_address": [3,5] }"""
SERVICE_BUSPRO_ACTIVATE_SCENE_SCHEMA = vol.Schema({
    vol.Required(SERVICE_BUSPRO_ATTR_ADDRESS): vol.Any([cv.positive_int]),
    vol.Required(SERVICE_BUSPRO_ATTR_SCENE_ADDRESS): vol.Any([cv.positive_int]),
})

"""{ "address": [1,74], "operate_code": [4,12], "payload": [1,75,0,3] }"""
SERVICE_BUSPRO_SEND_MESSAGE_SCHEMA = vol.Schema({
    vol.Required(SERVICE_BUSPRO_ATTR_ADDRESS): vol.Any([cv.positive_int]),
    vol.Required(SERVICE_BUSPRO_ATTR_OPERATE_CODE): vol.Any([cv.positive_int]),
    vol.Required(SERVICE_BUSPRO_ATTR_PAYLOAD): vol.Any([cv.positive_int]),
})

"""{ "address": [1,100], "switch_number": 100, "status": 1 }"""
SERVICE_BUSPRO_UNIVERSAL_SWITCH_SCHEMA = vol.Schema({
    vol.Required(SERVICE_BUSPRO_ATTR_ADDRESS): vol.Any([cv.positive_int]),
    vol.Required(SERVICE_BUSPRO_ATTR_SWITCH_NUMBER): vol.Any(cv.positive_int),
    vol.Required(SERVICE_BUSPRO_ATTR_STATUS): vol.Any(cv.positive_int),
})

CONFIG_SCHEMA = vol.Schema({
    DATA_BUSPRO: vol.Schema({
        vol.Required(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Required(CONF_BROADCAST_PORT): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_CONF_NAME): cv.string
    })
}, extra=vol.ALLOW_EXTRA)



async def _setup_buspro(hass: HomeAssistant, config_data: dict) -> bool:
    """Common initialization for both YAML and Config Entry."""
    if DATA_BUSPRO in hass.data:
        old_module = hass.data[DATA_BUSPRO]
        await old_module.stop(None)

    host = config_data.get(CONF_BROADCAST_ADDRESS, DEFAULT_BROADCAST_ADDRESS)
    port = config_data.get(CONF_BROADCAST_PORT, DEFAULT_BROADCAST_PORT)

    module = BusproModule(hass, host, port)
    await module.start()
    module.register_services()
    
    hass.data[DATA_BUSPRO] = module

    async def start_scheduler(_):
        await module.start_scheduler()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_scheduler)
    return True

async def async_setup(hass: HomeAssistant, config: dict):
    """Setup from YAML configuration."""
    if DATA_BUSPRO not in config:
        return True
    return await _setup_buspro(hass, config[DATA_BUSPRO])

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Setup from Config Entry (UI)."""    
    if (not hass.is_running) and (DATA_BUSPRO in hass.data):
        _LOGGER.debug("Home Assistant is starting and Buspro module already exists, skipping configuration")
        return True
        
    return await _setup_buspro(hass, config_entry.data)


class BusproModule:
    def __init__(self, hass, host, port):
        self.hass = hass
        self.connected = False        
        self.gateway_address_send_receive = ((host, port), ('', port))
        self.hdl = Buspro(self.gateway_address_send_receive, self.hass.loop)        
        self.scheduler = Scheduler(hass)
        self.entity_lock = asyncio.Lock()

    async def start(self):
        await self.hdl.start(state_updater=False)
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.stop)
        self.connected = True

    async def start_scheduler(self):
        await self.scheduler.read_entities_periodically()

    async def stop(self, event):
        await self.hdl.stop()

    async def entity_initialized(self, entity):
        async with self.entity_lock:
            _LOGGER.debug(f"Entity initialized: {entity.entity_id} with scan interval {entity.scan_interval}")
            await self.scheduler.add_entity(entity)


    async def service_activate_scene(self, call):
        """Service for activatign a __scene"""
        # noinspection PyUnresolvedReferences
        from .pybuspro.devices.scene import Scene

        attr_address = call.data.get(SERVICE_BUSPRO_ATTR_ADDRESS)
        attr_scene_address = call.data.get(SERVICE_BUSPRO_ATTR_SCENE_ADDRESS)
        scene = Scene(self.hdl, attr_address, attr_scene_address, DEFAULT_SCENE_NAME)
        await scene.run()

    async def service_send_message(self, call):
        """Service for send an arbitrary message"""
        # noinspection PyUnresolvedReferences
        from .pybuspro.devices.generic import Generic

        attr_address = call.data.get(SERVICE_BUSPRO_ATTR_ADDRESS)
        attr_payload = call.data.get(SERVICE_BUSPRO_ATTR_PAYLOAD)
        attr_operate_code = call.data.get(SERVICE_BUSPRO_ATTR_OPERATE_CODE)
        generic = Generic(self.hdl, attr_address, attr_payload, attr_operate_code, DEFAULT_SEND_MESSAGE_NAME)
        await generic.run()

    async def service_set_universal_switch(self, call):
        # noinspection PyUnresolvedReferences
        from .pybuspro.devices.universal_switch import UniversalSwitch

        attr_address = call.data.get(SERVICE_BUSPRO_ATTR_ADDRESS)
        attr_switch_number = call.data.get(SERVICE_BUSPRO_ATTR_SWITCH_NUMBER)
        universal_switch = UniversalSwitch(self.hdl, attr_address, attr_switch_number)

        status = call.data.get(SERVICE_BUSPRO_ATTR_STATUS)
        if status == 1:
            await universal_switch.set_on()
        else:
            await universal_switch.set_off()

    def register_services(self):

        """ activate_scene """
        self.hass.services.async_register(
            DATA_BUSPRO, SERVICE_BUSPRO_ACTIVATE_SCENE,
            self.service_activate_scene,
            schema=SERVICE_BUSPRO_ACTIVATE_SCENE_SCHEMA)

        """ send_message """
        self.hass.services.async_register(
            DATA_BUSPRO, SERVICE_BUSPRO_SEND_MESSAGE,
            self.service_send_message,
            schema=SERVICE_BUSPRO_SEND_MESSAGE_SCHEMA)

        """ universal_switch """
        self.hass.services.async_register(
            DATA_BUSPRO, SERVICE_BUSPRO_UNIVERSAL_SWITCH,
            self.service_set_universal_switch,
            schema=SERVICE_BUSPRO_UNIVERSAL_SWITCH_SCHEMA)

    '''
    def telegram_received_cb(self, telegram):
        #     """Call invoked after a KNX telegram was received."""
        #     self.hass.bus.fire('knx_event', {
        #         'address': str(telegram.group_address),
        #         'data': telegram.payload.value
        #     })
        # _LOGGER.info(f"Callback: '{telegram}'")
        return False
    '''

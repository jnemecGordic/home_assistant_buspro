import logging

from custom_components.buspro.const import DATA_BUSPRO
from .udp_client import UDPClient
from ..helpers.telegram_helper import TelegramHelper
# from ..devices.control import Control
import time
#_LOGGER = logging.getLogger(__name__)

class NetworkInterface:
    def __init__(self, hass, gateway_address_send_receive):
        self._hass = hass
        self.gateway_address_send_receive = gateway_address_send_receive
        self.udp_client = None
        self.callback = None
        self._init_udp_client()
        self._th = TelegramHelper()

    def _init_udp_client(self):
        self.udp_client = UDPClient(self._hass, self.gateway_address_send_receive, self._udp_request_received)

    def _udp_request_received(self, data, address):
        if self.callback is not None:
            telegram = self._th.build_telegram_from_udp_data(data, address)
            self.callback(telegram)

    """
    public methods
    """
    def register_callback(self, callback):
        self.callback = callback

    async def start(self):
        await self.udp_client.start()

    async def stop(self):
        if self.udp_client is not None:
            await self.udp_client.stop()
            self.udp_client = None

    async def send_telegram(self, telegram):
        #start_time = time.perf_counter_ns()
        message = self._th.build_send_buffer(telegram)
        #end_time = time.perf_counter_ns()
        #duration = end_time - start_time
        #_LOGGER.debug(f"Time to build send buffer: {duration} ns")
        gateway_address_send, _ = self.gateway_address_send_receive
        await self.udp_client.send_message(message)

        
        if self._hass.data[DATA_BUSPRO].hdl.logger.level == logging.DEBUG:
            self._hass.data[DATA_BUSPRO].hdl.logger.debug(self._th.build_telegram_from_udp_data(message, gateway_address_send))
            

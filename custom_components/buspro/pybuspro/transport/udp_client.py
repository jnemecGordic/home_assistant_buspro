import asyncio
import socket
import logging
from custom_components.buspro.const import DATA_BUSPRO


_LOGGER = logging.getLogger(__name__)

class UDPClient:

    class UDPClientFactory(asyncio.DatagramProtocol):

        def __init__(self, hass, data_received_callback=None):
            self.hass = hass  # Přejmenované pro konzistenci
            self.transport = None
            self.data_received_callback = data_received_callback

        def connection_made(self, transport):
            self.transport = transport

        def datagram_received(self, data, address):
            if self.data_received_callback is not None:
                self.data_received_callback(data, address)

        def error_received(self, exc):
            self.hass.data[DATA_BUSPRO].hdl.logger.warning('Error received: %s', exc)

        def connection_lost(self, exc):
            self.hass.data[DATA_BUSPRO].hdl.logger.info('closing transport %s', exc)

    def __init__(self, hass, gateway_address_send_receive, callback):
        self._hass = hass
        self._gateway_address_send, self._gateway_address_receive = gateway_address_send_receive
        self.callback = callback
        self.transport = None

    def _data_received_callback(self, data, address):
        self.callback(data, address)

    def _create_broadcast_sock(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)
            sock.bind(self._gateway_address_receive)
            return sock
        except Exception as ex:
            _LOGGER.warning("Could not connect to %s: %s", self._gateway_address_receive, ex)
            return None

    async def _connect(self):
        try:
            udp_client_factory = UDPClient.UDPClientFactory(
                self._hass,
                data_received_callback=self._data_received_callback
            )

            sock = self._create_broadcast_sock()
            if sock is None:
                _LOGGER.warning("Socket is None")
                return

            loop = asyncio.get_event_loop()
            (transport, _) = await loop.create_datagram_endpoint(
                lambda: udp_client_factory, 
                sock=sock
            )
            self.transport = transport

        except Exception as ex:
            _LOGGER.warning("Could not create endpoint to %s: %s", 
                          self._gateway_address_receive, ex)

    async def start(self):
        await self._connect()

    async def stop(self):
        if self.transport is not None:
            self.transport.close()

    async def send_message(self, message):
        if self.transport is not None:
            self.transport.sendto(message, self._gateway_address_send)
        else:
            self._hass.data[DATA_BUSPRO].hdl.logger.info("Could not send message. Transport is None.")

﻿import asyncio

from custom_components.buspro.const import DATA_BUSPRO


from .control import _ReadStatusOfChannels


class Device(object):
    def __init__(self, hass, device_address, name=""):
        # device_address = (subnet_id, device_id, ...)

        self._device_address = device_address
        self._hass = hass
        self._name = name
        self.device_updated_cbs = []

    @property
    def name(self):
        return self._name

    def register_telegram_received_cb(self, telegram_received_cb):
        self._hass.data[DATA_BUSPRO].hdl.register_telegram_received_device_cb(
            telegram_received_cb, 
            self._device_address
        )

    def unregister_telegram_received_cb(self, telegram_received_cb):
        self._buspro.unregister_telegram_received_device_cb(telegram_received_cb, self._device_address)

    def register_device_updated_cb(self, device_updated_cb):
        """Register device updated callback."""
        self.device_updated_cbs.append(device_updated_cb)

    def unregister_device_updated_cb(self, device_updated_cb):
        """Unregister device updated callback."""
        self.device_updated_cbs.remove(device_updated_cb)

    async def _device_updated(self, should_reschedule=True):
        """Device update callback with scheduler reset flag."""
        for device_updated_cb in self.device_updated_cbs:
            if hasattr(device_updated_cb, '__code__') and 'should_reschedule' in device_updated_cb.__code__.co_varnames:
                await device_updated_cb(self, should_reschedule)
            else:
                await device_updated_cb(self)

    async def _send_telegram(self, telegram):
        await self._buspro.network_interface.send_telegram(telegram)

    def _call_device_updated(self, should_reschedule=True):
        """Call device updated with scheduler reset flag."""
        asyncio.ensure_future(self._device_updated(should_reschedule), loop=self._hass.data[DATA_BUSPRO].hdl.loop)

    def _call_read_current_status_of_channels(self, run_from_init=False):
        async def read_current_state_of_channels():
            if run_from_init:
                await asyncio.sleep(5)
            
            read_status_of_channels = _ReadStatusOfChannels(self._hass, self._device_address)
            await read_status_of_channels.send()

        asyncio.ensure_future(
            read_current_state_of_channels(), 
            loop=self._hass.data[DATA_BUSPRO].hdl.loop
        )

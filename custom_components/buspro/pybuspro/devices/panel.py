import logging
from .device import Device
from ..helpers.enums import OperateCode
from .control import _PanelControl, _ReadPanelStatus

_LOGGER = logging.getLogger(__name__)

PANEL_CONTROL_REMARK = 18

class Panel(Device):
    """HDL panel device for handling button presses and other panel-related operations."""
    
    def __init__(self, buspro, device_address, channel_number: int, name=""):
        super().__init__(buspro, device_address, name)
        self._buspro = buspro
        self._device_address = device_address
        self._name = name
        self._channel_number = channel_number
        self._is_on = False
        self._callbacks = []
        
        self.register_telegram_received_cb(self._telegram_received_cb)

    def _telegram_received_cb(self, telegram):
        """Handle received telegrams from panel."""
        
        if telegram.operate_code in [OperateCode.ReadPanelStatusResponse,OperateCode.PanelControlResponse]:
            if telegram.payload[0] == PANEL_CONTROL_REMARK and self._channel_number == telegram.payload[1]:
                self._is_on = telegram.payload[2] == 1
                _LOGGER.debug(f"Panel status received for button {self._channel_number} at {self._device_address} is {self._is_on}")
                self._call_device_updated()

    async def press_button(self, button_number: int, value: bool = False):
        """Send panel control command for button press."""
        _LOGGER.debug(f"Sending panel control for button {button_number} at {self._device_address} with value {value}")
        pc = _PanelControl(self._buspro, self._device_address)        
        pc.remark = PANEL_CONTROL_REMARK
        pc.key_number = button_number
        pc.key_status = 1 if value else 0
        await pc.send()

    async def set_on(self):
        """Turn on the channel."""
        await self.press_button(self._channel_number, True)
        self._is_on = True
        self._call_device_updated()

    async def set_off(self):
        """Turn off the channel."""
        await self.press_button(self._channel_number, False)
        self._is_on = False
        self._call_device_updated()

    async def read_status(self):
        """Read channel status."""
        rps = _ReadPanelStatus(self._buspro, self._device_address)        
        rps.key_number = self._channel_number
        rps.remark = PANEL_CONTROL_REMARK
        await rps.send()

    @property
    def is_on(self):
        """Return if channel is on."""
        return self._is_on




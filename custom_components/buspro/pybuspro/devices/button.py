import logging
from .device import Device
from ..helpers.enums import OperateCode
from .control import _PanelControl

_LOGGER = logging.getLogger(__name__)

class Button(Device):
    """HDL button device."""
    
    def __init__(self, buspro, device_address, button_number, name=""):
        super().__init__(buspro, device_address, name)
        self._button_number = button_number
        self._buspro = buspro
        self._device_address = device_address
        self._name = name

    async def press(self, value=False):
        """Send panel control command."""
        _LOGGER.debug(f"Sending panel control for button {self._button_number} at {self._device_address} with value {value}")

        pc = _PanelControl(self._buspro)
        pc.subnet_id, pc.device_id = self._device_address
        pc.remark = 18
        pc.key_number = self._button_number
        pc.key_status = 1 if value else 0
        await pc.send()


    @property
    def button_number(self):
        """Return button number."""
        return self._button_number

    @property
    def device_identifier(self):
        """Return unique ID."""
        return f"{self._device_address}-button-{self._button_number}"
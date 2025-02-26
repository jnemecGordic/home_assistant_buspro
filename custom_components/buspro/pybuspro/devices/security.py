"""HDL Buspro security/alarm module implementation."""
from enum import IntEnum
import logging
from typing import Tuple, Optional, List, Callable

from custom_components.buspro.pybuspro.devices.control import _ArmSecurityModule, _ReadSecurityModule

from ..helpers.enums import OperateCode
from .device import Device

_LOGGER = logging.getLogger(__name__)

class SecurityStatus(IntEnum):
    """Security module status codes."""
    VACATION = 1      # Vacation mode
    AWAY = 2          # Away mode
    NIGHT = 3         # Night mode
    NIGHT_WITH_GUEST = 4  # Night mode with guests
    DAY = 5           # Day mode
    DISARM = 6        # Disarmed

class Security(Device):
    """HDL Buspro security/alarm device."""
    
    def __init__(self, buspro, device_address: Tuple[int, int], area_id: int = 1, name=""):
        """Initialize security device.
        
        Args:
            buspro: HDL Buspro instance
            device_address: Tuple of (subnet_id, device_id)
            area_id: Area ID (1-8)
            name: Device name
        """
        super().__init__(buspro, device_address, name)
        self._status = None
        self._area_id = area_id        
        self._device_address = device_address

        self.register_telegram_received_cb(self._telegram_received_cb)
        _LOGGER.debug(f"Initialized security device {device_address} for area {area_id}")
        

    def _telegram_received_cb(self, telegram):
        """Handle received telegram."""        
        if telegram.operate_code in [OperateCode.ReadSecurityModuleResponse, OperateCode.ArmSecurityModuleResponse]:
            if len(telegram.payload) > 1 and telegram.payload[0] == self._area_id and telegram.payload[1] >= 1 and telegram.payload[1] <= 6:
                self._status = SecurityStatus(telegram.payload[1])
                self._call_device_updated()

    async def read_security_status(self):
        """Read current security status from device."""
        rsm = _ReadSecurityModule(self._buspro, self._device_address)
        rsm.area = self._area_id
        await rsm.send()

    async def set_status(self, status: SecurityStatus):
        """Set security module status."""
        if status not in SecurityStatus:
            _LOGGER.error(f"Invalid security status: {status}")
            return

        _LOGGER.debug(f"Setting security module {self._device_address} area {self._area_id} "
                     f"status to {status.name} (value: {status.value})")

        control = _ArmSecurityModule(self._buspro, self._device_address)
        control.area = self._area_id
        if status != SecurityStatus.DISARM:
            control.arm_type = SecurityStatus.DISARM.value
            await control.send()

        control.arm_type = status.value        
        await control.send()
        

    @property
    def status(self) -> SecurityStatus:
        """Get current security status."""
        return self._status


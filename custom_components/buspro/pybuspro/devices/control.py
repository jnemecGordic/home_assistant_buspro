import logging

from custom_components.buspro.const import DATA_BUSPRO

from ..core.telegram import Telegram
from ..helpers.enums import OperateCode
_LOGGER = logging.getLogger(__name__)

class _Control:
    def __init__(self, hass, device_address):
        self._hass = hass
        self.subnet_id = device_address[0]
        self.device_id = device_address[1]
        #if _LOGGER.isEnabledFor(logging.DEBUG):
        #    _LOGGER.debug("Control device_address: {}".format(device_address))

    @staticmethod
    def build_telegram_from_control(control):

        if control is None:
            return None

        if type(control) == _SingleChannelControl:
            operate_code = OperateCode.SingleChannelControl
            payload = [control.channel_number, control.channel_level, control.running_time_minutes,
                       control.running_time_seconds]

        elif type(control) == _SceneControl:
            operate_code = OperateCode.SceneControl
            payload = [control.area_number, control.scene_number]

        elif type(control) == _ReadStatusOfChannels:
            operate_code = OperateCode.ReadStatusOfChannels
            payload = []

        elif type(control) == _GenericControl:
            operate_code = control.operate_code
            payload = control.payload

        elif type(control) == _UniversalSwitch:
            operate_code = OperateCode.UniversalSwitchControl
            payload = [control.switch_number, control.switch_status.value]

        elif type(control) == _PanelControl:
            operate_code = OperateCode.PanelControl
            payload = [control.remark, control.key_number, control.key_status]

        elif type(control) == _ReadPanelStatus:
            operate_code = OperateCode.ReadPanelStatus
            payload = [control.remark, control.key_number]            

        elif type(control) == _ReadStatusOfUniversalSwitch:
            operate_code = OperateCode.ReadStatusOfUniversalSwitch
            payload = [control.switch_number]

        elif type(control) == _ReadStatusOfSwitch:
            operate_code = OperateCode.ReadStatusOfChannels
            payload = []

        elif type(control) == _Read12in1SensorStatus:
            operate_code = OperateCode.Read12in1SensorStatus
            payload = []

        elif type(control) == _ReadSensorsInOneStatus:
            operate_code = OperateCode.ReadSensorsInOneStatus
            payload = []

        elif type(control) == _ReadTemperatureStatus:
            operate_code = OperateCode.ReadTemperatureStatus
            payload = [control.channel_number]

        elif type(control) == _ReadFloorHeatingStatus:
            operate_code = OperateCode.ReadFloorHeatingStatus
            payload = []

        elif type(control) == _ReadDryContactStatus:
            operate_code = OperateCode.ReadDryContactStatus
            payload = [1, control.switch_number]

        elif type(control) == _ControlFloorHeatingStatus:
            operate_code = OperateCode.ControlFloorHeatingStatus
            payload = [control.temperature_type, control.status, control.mode, control.normal_temperature,
                       control.day_temperature, control.night_temperature, control.away_temperature]
            
        elif type(control) == _CurtainSwitchControl:
            operate_code = OperateCode.CurtainSwitchControl
            payload = [control.channel,control.state]

        elif type(control) == _CurtainReadStatus:
            operate_code = OperateCode.ReadStatusofCurtainSwitch
            payload = [control.channel]
        
        elif type(control) == _ReadSecurityModule:
            operate_code = OperateCode.ReadSecurityModule
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"ReadSecurityModule: {control.area}")
            payload = [control.area]            

        elif type(control) == _ArmSecurityModule:
            operate_code = OperateCode.ArmSecurityModule
            payload = [control.area,control.arm_type]
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"ArmSecurityModule: {control.area} : {control.arm_type}")

        elif type(control) == _AlarmSecurityModule:
            operate_code = OperateCode.AlarmSecurityModule
            payload = [control.area,0,0]

        elif type(control) in [_ModifySystemDateandTime,_BroadcastSystemDateandTimeEveryMinute]:
            if type(control) == _ModifySystemDateandTime:
                operate_code = OperateCode.ModifySystemDateandTime
            else:    
                operate_code = OperateCode.BroadcastSystemDateandTimeEveryMinute                        
            now = control.custom_datetime
            payload = [
                now.year - 2000,
                now.month,
                now.day,
                now.hour,
                now.minute,
                now.second,
                (now.weekday() + 1) % 7
            ]

        else:
            return None

        telegram = Telegram()
        telegram.target_address = (control.subnet_id, control.device_id)
        telegram.operate_code = operate_code
        telegram.payload = payload
        return telegram

    @property
    def telegram(self):
        return self.build_telegram_from_control(self)

    async def send(self):
        telegram = self.telegram
        await self._hass.data[DATA_BUSPRO].hdl.network_interface.send_telegram(telegram)


class _GenericControl(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)

        self.payload = None
        self.operate_code = None


class _SingleChannelControl(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)

        self.channel_number = None
        self.channel_level = None
        self.running_time_minutes = None
        self.running_time_seconds = None


class _SceneControl(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)

        self.area_number = None
        self.scene_number = None


class _ReadStatusOfChannels(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
        # no more properties


class _UniversalSwitch(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)

        self.switch_number = None
        self.switch_status = None


class _ReadStatusOfUniversalSwitch(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)

        self.switch_number = None

class _ReadStatusOfSwitch(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)


class _Read12in1SensorStatus(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
        # no more properties


class _ReadSensorsInOneStatus(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
        # no more properties


class _ReadTemperatureStatus(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
        self.channel_number = None


class _ReadFloorHeatingStatus(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
        # no more properties


class _ControlFloorHeatingStatus(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)

        self.temperature_type = None
        self.status = None
        self.mode = None
        self.normal_temperature = None
        self.day_temperature = None
        self.night_temperature = None
        self.away_temperature = None


class _ReadDryContactStatus(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)

        self.switch_number = None


class _PanelControl(_Control):
    """Panel control command."""    
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
                
        self.remark = None
        self.key_number = None
        self.key_status = None

class _ReadPanelStatus(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
                
        self.remark = None
        self.key_number = None
        
class _CurtainSwitchControl(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
                
        self.channel = None
        self.state = None

class _CurtainReadStatus(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
                        
        self.channel = None
        

class _ReadSecurityModule(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
                        
        self.area = None

class _ArmSecurityModule(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
                        
        self.area = None
        self.arm_type = None
        
class _AlarmSecurityModule(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
                        
        self.area = None
        

class _ModifySystemDateandTime(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
        self.custom_datetime = None

class _BroadcastSystemDateandTimeEveryMinute(_Control):
    def __init__(self, hass, device_address):
        super().__init__(hass, device_address)
        self.custom_datetime = None


import traceback
from struct import *

import crcmod

from .enums import DeviceType
from .generics import Generics
from ..core.telegram import Telegram
from ..devices.control import *
_LOGGER = logging.getLogger(__name__)

class TelegramHelper:    
    IDX_LENGTH = 16
    IDX_SRC_SUBNET = 17
    IDX_SRC_DEVICE = 18
    IDX_DEV_TYPE = 19
    IDX_OP_CODE = 21
    IDX_TGT_SUBNET = 23
    IDX_TGT_DEVICE = 24
    IDX_CONTENT = 25
    CONTENT_LENGTH_OFFSET = 11
    HDL_HEADER = b'\xC0\xA8\x01\x0FHDLMIRACLE\xAA\xAA'
    
    def __init__(self):
        """Initialize the telegram helper."""
        self.crc16func = crcmod.mkCrcFun(0x11021, initCrc=0, rev=False, xorOut=0)

    def build_telegram_from_udp_data(self, data, address):
        """Build telegram from UDP data."""
        if not data:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("build_telegram_from_udp_data: no data")
            return None

        try:
            # Get length and calculate content length
            length_of_data_package = data[self.IDX_LENGTH]
            content_length = length_of_data_package - self.CONTENT_LENGTH_OFFSET
            
            # Extract device info and addresses
            source_subnet_id = data[self.IDX_SRC_SUBNET]
            source_device_id = data[self.IDX_SRC_DEVICE]
            source_device_type_hex = data[self.IDX_DEV_TYPE:self.IDX_DEV_TYPE + 2]
            operate_code_hex = data[self.IDX_OP_CODE:self.IDX_OP_CODE + 2]
            target_subnet_id = data[self.IDX_TGT_SUBNET]
            target_device_id = data[self.IDX_TGT_DEVICE]
            
            # Extract content and CRC
            content = data[self.IDX_CONTENT:self.IDX_CONTENT + content_length]
            crc = data[-2:]

            # Create and populate telegram
            generics = Generics()
            telegram = Telegram()
            telegram.source_device_type = generics.get_enum_value(DeviceType, source_device_type_hex)
            telegram.udp_data = data
            telegram.source_address = (source_subnet_id, source_device_id)
            telegram.operate_code = generics.get_enum_value(OperateCode, operate_code_hex)
            telegram.target_address = (target_subnet_id, target_device_id)
            telegram.udp_address = address
            telegram.payload = generics.hex_to_integer_list(content)
            telegram.crc = crc

            # Validate CRC
            if not self._check_crc(telegram):
                _LOGGER.error("CRC check failed")
                return None

            return telegram
            
        except Exception as e:
            _LOGGER.error(f"Error building telegram: {traceback.format_exc()}")
            return None

    def build_send_buffer(self, telegram: Telegram):
        """Optimized version of build_send_buffer."""
        if telegram is None:
            return None

        # Calculate payload length and total buffer size 
        payload = telegram.payload or []
        length_of_data_package = 11 + len(payload)
        buffer_size = 16 + length_of_data_package  # Pre-allocate correct size
        
        # Create buffer with pre-allocated size
        send_buf = bytearray(buffer_size)
        
        # Insert fixed header (preprocessed constant data)        
        send_buf[:16] = self.HDL_HEADER
        
        # Insert packet length
        send_buf[16] = length_of_data_package        
        
        # Process source address
        if telegram.source_address is not None:
            send_buf[17] = telegram.source_address[0]  # sender_subnet_id
            send_buf[18] = telegram.source_address[1]  # sender_device_id
        else:
            send_buf[17] = 254
            send_buf[18] = 253        
        
        # Process device type
        #if telegram.source_device_type is not None:
        #    source_device_type_hex = telegram.source_device_type.value
        #    send_buf[19:21] = bytes(source_device_type_hex)
        #else:
        send_buf[19:21] = b'\xFF\xFC'
        
        # Insert operate code
        operate_code_hex = telegram.operate_code.value
        send_buf[21:23] = bytes(operate_code_hex)
        
        # Insert target address
        target_subnet_id, target_device_id = telegram.target_address
        send_buf[23] = target_subnet_id
        send_buf[24] = target_device_id        
        
        # Insert payload in single operation
        if payload:
            send_buf[25:25+len(payload)] = bytes(payload)        
        
        # Calculate and add CRC
        crc = self.crc16func(send_buf[16:16+length_of_data_package-2])
        send_buf[25+len(payload):] = pack(">H", crc)
        return send_buf

    def _calculate_crc(self, length_of_data_package, send_buf):
        crc_buf_length = length_of_data_package - 2
        crc_buf = send_buf[-crc_buf_length:]
        crc_buf_as_bytes = bytes(crc_buf)
        crc = self.crc16func(crc_buf_as_bytes)

        return pack(">H", crc)

    def _calculate_crc_from_telegram(self, telegram):
        length_of_data_package = 11 + len(telegram.payload)
        crc_buf_length = length_of_data_package - 2
        send_buf = telegram.udp_data[:-2]
        crc_buf = send_buf[-crc_buf_length:]
        crc_buf_as_bytes = bytes(crc_buf)
        crc = self.crc16func(crc_buf_as_bytes)
        
        return pack(">H", crc)

    def _check_crc(self, telegram):        
        calculated_crc = self._calculate_crc_from_telegram(telegram)
        if calculated_crc == telegram.crc:
            return True
        return False




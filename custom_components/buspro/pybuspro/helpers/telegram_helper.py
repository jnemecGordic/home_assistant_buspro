import traceback
from struct import *

from .enums import DeviceType
from .generics import Generics
from ..core.telegram import Telegram
from ..devices.control import *
_LOGGER = logging.getLogger(__name__)

class TelegramHelper:
    # Konstanty pro indexy v telegramu
    IDX_LENGTH = 16
    IDX_SRC_SUBNET = 17
    IDX_SRC_DEVICE = 18
    IDX_DEV_TYPE = 19
    IDX_OP_CODE = 21
    IDX_TGT_SUBNET = 23
    IDX_TGT_DEVICE = 24
    IDX_CONTENT = 25
    CONTENT_LENGTH_OFFSET = 11

    CRC16_CCITT_TABLE = [
        0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7, 0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
        0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6, 0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
        0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485, 0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
        0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4, 0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
        0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823, 0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
        0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12, 0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
        0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41, 0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
        0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70, 0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
        0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F, 0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E, 0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D, 0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C, 0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB, 0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
        0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A, 0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
        0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9, 0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
        0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8, 0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
    ]

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
        header = b'\xC0\xA8\x01\x0FHDLMIRACLE\xAA\xAA'
        send_buf[:16] = header       
        
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
        crc_buf = send_buf[16:16+length_of_data_package-2]
        crc = self._crc16(bytes(crc_buf))
        crc_bytes = pack(">H", crc)
        send_buf[25+len(payload):] = crc_bytes        
        return send_buf

    def _calculate_crc(self, length_of_data_package, send_buf):
        crc_buf_length = length_of_data_package - 2
        crc_buf = send_buf[-crc_buf_length:]
        crc_buf_as_bytes = bytes(crc_buf)
        crc = self._crc16(crc_buf_as_bytes)

        return pack(">H", crc)

    def _calculate_crc_from_telegram(self, telegram):
        length_of_data_package = 11 + len(telegram.payload)
        crc_buf_length = length_of_data_package - 2
        send_buf = telegram.udp_data[:-2]
        crc_buf = send_buf[-crc_buf_length:]
        crc_buf_as_bytes = bytes(crc_buf)
        crc = self._crc16(crc_buf_as_bytes)
        
        return pack(">H", crc)

    def _check_crc(self, telegram):
        # crc = data[-2:]
        calculated_crc = self._calculate_crc_from_telegram(telegram)
        if calculated_crc == telegram.crc:
            return True
        return False

    @staticmethod
    def _crc16(data: bytes) -> int:        
        crc = 0x0000
        table = TelegramHelper.CRC16_CCITT_TABLE       
        
        view = memoryview(data).tobytes()
        for b in view:
            crc = ((crc << 8) & 0xFF00) ^ table[((crc >> 8) ^ b) & 0xFF]
            
        return crc

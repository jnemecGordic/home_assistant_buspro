import asyncio
import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

async def wait_for_buspro(hass: HomeAssistant, data_key: str, timeout: int = 600) -> bool:
    """Wait for buspro component to be ready."""        
    for _ in range(timeout):
        if data_key in hass.data:
            return True
        await asyncio.sleep(0.1)
        
    return False

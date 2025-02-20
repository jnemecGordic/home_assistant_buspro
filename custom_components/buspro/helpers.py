import asyncio
import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Globální event pro signalizaci inicializace
BUSPRO_READY = asyncio.Event()

async def wait_for_buspro(hass: HomeAssistant, data_key: str, timeout: int = 60) -> bool:        
    if data_key in hass.data:
        return True
    try:
        await asyncio.wait_for(BUSPRO_READY.wait(), timeout=timeout)
        return data_key in hass.data
    except asyncio.TimeoutError:
        return False

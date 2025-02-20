import asyncio
import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
_SETUP_COMPLETE = asyncio.Event()

async def wait_for_buspro(hass: HomeAssistant, data_key: str, timeout: int = 60) -> bool:
    """Wait for buspro component to be ready."""        
    for _ in range(timeout):
        if data_key in hass.data:
            return True
        try:
            await asyncio.wait_for(_SETUP_COMPLETE.wait(), timeout=1)
        except asyncio.TimeoutError:
            continue
        
    return False

def signal_buspro_ready():
    """Signal that Buspro setup is complete."""
    _SETUP_COMPLETE.set()
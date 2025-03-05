import asyncio
import logging
from homeassistant.core import HomeAssistant

from custom_components.buspro.const import DATA_BUSPRO

_LOGGER = logging.getLogger(__name__)
_SETUP_COMPLETE = asyncio.Event()

async def wait_for_buspro(hass: HomeAssistant, timeout: int = 60) -> bool:
    """Wait for buspro component to be ready."""        
    for _ in range(timeout):
        if DATA_BUSPRO in hass.data:
            return True
        try:
            await asyncio.wait_for(_SETUP_COMPLETE.wait(), timeout=1)
        except asyncio.TimeoutError:
            continue
        
    return False

def signal_buspro_ready():
    """Signal that Buspro setup is complete."""
    _SETUP_COMPLETE.set()
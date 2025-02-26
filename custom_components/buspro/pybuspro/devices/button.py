import logging
from .device import Device
from ..helpers.enums import OperateCode
from .control import _PanelControl
from .panel import Panel

_LOGGER = logging.getLogger(__name__)

class Button:
    """Representation of a single button on a HDL panel."""
    
    def __init__(self, panel, button_number: int, name: str = ""):
        """Initialize the button.
        
        Args:
            panel: Panel device instance
            button_number: Button number on the panel
            name: Optional name for the button
        """
        self._panel = panel
        self._button_number = button_number
        self._name = name

    async def press(self, value: bool = False):
        """Press the button."""
        await self._panel.press_button(self._button_number, value)

    @property
    def button_number(self):
        """Return button number."""
        return self._button_number

    @property
    def name(self):
        """Return the display name of this button."""
        return self._name

"""Errors for the digitalSTROM component."""
from homeassistant.exceptions import HomeAssistantError


class DigitalstromException(HomeAssistantError):
    """Base class for digitalSTROM exceptions."""
    pass


class AlreadyConfigured(DigitalstromException):
    """Device is already configured."""
    pass


class CannotConnect(DigitalstromException):
    """Unable to connect to the device."""
    pass

"""The digitalSTROM integration."""
import asyncio
import logging
import socket
import urllib3

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ALIAS,
    CONF_TOKEN,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady, InvalidStateError
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    HOST_FORMAT,
    SLUG_FORMAT,
    CONF_DELAY,
    DEFAULT_DELAY,
)
from .util import slugify_entry

_LOGGER = logging.getLogger(__name__)

COMPONENT_TYPES = ["light", "switch", "cover", "scene"]


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """
    load configuration for digitalSTROM component
    """
    # not configured
    if DOMAIN not in config:
        return True

    # already imported
    if hass.config_entries.async_entries(DOMAIN):
        return True

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """
    set up digitalSTROM component from config entry
    """
    _LOGGER.debug("digitalstrom setup started")

    # import libraries
    from pydigitalstrom.client import DSClient
    from pydigitalstrom.exceptions import DSException
    from pydigitalstrom.websocket import DSWebsocketEventListener

    # initialize component data
    hass.data.setdefault(DOMAIN, dict())

    # old installations don't have an app token in their config entry
    if not entry.data.get(CONF_TOKEN, None):
        raise InvalidStateError(
            "No app token in config entry, please re-setup the integration"
        )

    # setup client and listener
    client = DSClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        apptoken=entry.data[CONF_TOKEN],
        apartment_name=entry.data[CONF_ALIAS],
        stack_delay=entry.data.get(CONF_DELAY, DEFAULT_DELAY),
        loop=hass.loop,
    )
    listener = DSWebsocketEventListener(client=client, event_name="callScene")

    # store client in hass data for future usage
    entry_slug = slugify_entry(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
    hass.data[DOMAIN].setdefault(entry_slug, dict())
    hass.data[DOMAIN][entry_slug]["client"] = client
    hass.data[DOMAIN][entry_slug]["listener"] = listener

    # async def digitalstrom_discover_devices(event):
    # load all scenes from digitalSTROM server
    try:
        await client.initialize()
    except (DSException, RuntimeError, ConnectionResetError):
        raise ConfigEntryNotReady(
            "Failed to initialize digitalSTROM server at %s", client.host
        )

    # we're connected
    _LOGGER.debug(
        "Successfully retrieved session token from digitalSTROM server at %s",
        client.host,
    )

    # register devices
    for component in COMPONENT_TYPES:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    # start websocket listener and action delayer loops on hass startup
    async def digitalstrom_start_loops(event):
        _LOGGER.debug(f"loops started for digitalSTROM server at {client.host}")
        hass.async_add_job(listener.start)
        hass.async_add_job(client.stack.start)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, digitalstrom_start_loops)

    # start websocket listener and action delayer loops on hass shutdown
    async def digitalstrom_stop_loops(event):
        _LOGGER.debug(f"loops stopped for digitalSTROM server at {client.host}")
        hass.async_add_job(client.stack.stop)
        hass.async_add_job(listener.stop)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, digitalstrom_stop_loops)

    return True

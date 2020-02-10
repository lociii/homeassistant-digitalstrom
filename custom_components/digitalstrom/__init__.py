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
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    DOMAIN_LISTENER,
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
    hass.data.setdefault(DOMAIN_LISTENER, dict())

    # old installations don't have an app token in their config entry
    if not entry.data.get(CONF_TOKEN, None):
        raise PlatformNotReady(
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
    hass.data[DOMAIN][entry_slug] = client
    hass.data[DOMAIN_LISTENER][entry_slug] = listener

    # async def digitalstrom_discover_devices(event):
    # load all scenes from digitalSTROM server
    try:
        await client.initialize()
    except (DSException, RuntimeError):
        _LOGGER.debug(
            "First connection to digitalSTROM server at %s failed - let's retry once",
            client.host,
        )

        # sleep for a second and retry - somehow these ds appliances
        # like to fail our first request
        await asyncio.sleep(1)
        try:
            await client.initialize()
        except (DSException, RuntimeError):
            raise PlatformNotReady(
                "Failed to initialize digitalSTROM server at %s", client.host
            )
    _LOGGER.debug(
        "Successfully retrieved session token from digitalSTROM server at %s",
        client.host,
    )

    # register devices
    for component in COMPONENT_TYPES:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    # start loops on home assistant startup
    async def digitalstrom_start_loops(event):
        _LOGGER.debug("loops started for digitalSTROM server at {}".format(client.host))
        hass.async_add_job(listener.start)
        hass.async_add_job(client.stack.start)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, digitalstrom_start_loops)

    # stop loops on home assistant shutdown
    async def digitalstrom_stop_loops(event):
        _LOGGER.debug("loops stopped for digitalSTROM server at {}".format(client.host))
        hass.async_add_job(client.stack.stop)
        hass.async_add_job(listener.stop)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, digitalstrom_stop_loops)

    return True

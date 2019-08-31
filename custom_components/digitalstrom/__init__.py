"""The digitalSTROM integration."""
import logging

from homeassistant import config_entries
from homeassistant.components.digitalstrom.util import slugify_entry
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ALIAS,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.util import slugify

from .const import DOMAIN, DOMAIN_LISTENER, CONFIG_PATH, HOST_FORMAT, SLUG_FORMAT

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
    import urllib3
    from pydigitalstrom.client import DSClient
    from pydigitalstrom.exceptions import DSException

    # disable urllib ssl warnings since most dss servers don't use certificates
    urllib3.disable_warnings()

    # initialize component data
    hass.data.setdefault(DOMAIN, dict())

    # get/validate apptoken
    device_slug = slugify_entry(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
    client = DSClient(
        host=HOST_FORMAT.format(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        apartment_name=entry.data[CONF_ALIAS],
        config_path=hass.config.path(CONFIG_PATH.format(host=entry.data[CONF_HOST])),
    )
    hass.data[DOMAIN][device_slug] = client
    try:
        await client.get_application_token()
    except DSException:
        raise PlatformNotReady(
            "Failed to retrieve apptoken from digitalSTROM server at %s", client.host
        )

    _LOGGER.debug(
        "Successfully retrieved apptoken from digitalSTROM server at %s", client.host
    )

    # load all scenes from digitalSTROM server
    await client.initialize()

    # register devices
    for component in COMPONENT_TYPES:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    # set up the listener that polls changes every second
    _LOGGER.debug("preparing event listener for digitalSTROM server at %s", client.host)
    from pydigitalstrom.listener import DSEventListener

    hass.data[DOMAIN].setdefault(DOMAIN_LISTENER, dict())
    event_listener = DSEventListener(
        client=client, event_id=1, event_name="callScene", timeout=1, loop=hass.loop
    )
    hass.data[DOMAIN][DOMAIN_LISTENER][device_slug] = event_listener

    # start listener on home assistant startup
    @callback
    def digitalstrom_start_listener(_):
        _LOGGER.debug(
            "event listener started for digitalSTROM server at {}".format(client.host)
        )
        hass.async_add_job(event_listener.start)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, digitalstrom_start_listener)

    # stop listener on home assistant shutdown
    @callback
    def digitalstrom_stop_listener(_):
        _LOGGER.debug(
            "event listener stopped for digitalSTROM server at {}".format(client.host)
        )
        hass.async_add_job(event_listener.stop)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, digitalstrom_stop_listener)

    return True

"""The digitalSTROM integration."""
import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, CONF_ALIAS,
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)
from homeassistant.core import callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.util import slugify

from .const import (
    DOMAIN, DOMAIN_LISTENER, CONFIG_PATH, HOST_FORMAT, SLUG_FORMAT)

_LOGGER = logging.getLogger(__name__)

COMPONENT_TYPES = ['light', 'switch', 'cover', 'scene']


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

    # import yaml config
    hass.async_create_task(hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_IMPORT},
        data=config[DOMAIN]
    ))
    return True


async def async_setup_entry(
        hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """
    set up digitalSTROM component from config entry
    """
    _LOGGER.debug('digitalstrom setup started')

    # import libraries
    import urllib3
    from pydigitalstrom.client import DSClient
    from pydigitalstrom.exceptions import DSException

    # disable urllib ssl warnings since most dss servers don't use certificates
    urllib3.disable_warnings()

    # initialize component data
    hass.data.setdefault(DOMAIN, dict())

    # get/validate apptoken
    slug = slugify(SLUG_FORMAT.format(
        host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]))
    hass.data[DOMAIN][slug] = DSClient(
        host=HOST_FORMAT.format(
            host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        apartment_name=entry.data[CONF_ALIAS],
        config_path=hass.config.path(CONFIG_PATH.format(
            host=entry.data[CONF_HOST])))
    try:
        await hass.data[DOMAIN][slug].get_application_token()
    except DSException:
        raise PlatformNotReady(
            'Failed to retrieve apptoken from digitalSTROM server at %s',
            hass.data[DOMAIN][slug].host)

    _LOGGER.debug(
        'Successfully retrieved apptoken from digitalSTROM server at %s',
        hass.data[DOMAIN][slug].host)

    # load all scenes from digitalSTROM server
    await hass.data[DOMAIN][slug].initialize()

    # register devices
    for component in COMPONENT_TYPES:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                entry, component))

    # set up the listener that polls changes every second
    _LOGGER.debug('preparing event listener for digitalSTROM server at %s',
                  hass.data[DOMAIN][slug].host)
    from pydigitalstrom.listener import DSEventListener
    hass.data[DOMAIN].setdefault(DOMAIN_LISTENER, dict())
    hass.data[DOMAIN][DOMAIN_LISTENER][slug] = DSEventListener(
        client=hass.data[DOMAIN][slug], event_id=1, event_name='callScene',
        timeout=1, loop=hass.loop)

    # start listener on home assistant startup
    @callback
    def digitalstrom_start_listener(_):
        _LOGGER.debug(
            'event listener started for digitalSTROM server at {}'.format(
                hass.data[DOMAIN][slug].host))
        hass.async_add_job(hass.data[DOMAIN][DOMAIN_LISTENER][slug].start)
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_START, digitalstrom_start_listener)

    # stop listener on home assistant shutdown
    @callback
    def digitalstrom_stop_listener(_):
        _LOGGER.debug(
            'event listener stopped for digitalSTROM server at {}'.format(
                hass.data[DOMAIN][slug].host))
        hass.async_add_job(hass.data[DOMAIN][DOMAIN_LISTENER][slug].stop)
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, digitalstrom_stop_listener)

    return True

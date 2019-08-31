"""Config flow to configure the digitalSTROM component."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.digitalstrom.const import DEFAULT_ALIAS, DEFAULT_HOST
from homeassistant.components.digitalstrom.util import slugify_entry
from homeassistant.components.ssdp import ATTR_MANUFACTURER, ATTR_HOST, ATTR_NAME
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ALIAS,
)
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONFIG_PATH,
    HOST_FORMAT,
    DIGITALSTROM_MANUFACTURERS,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    TITLE_FORMAT,
)


@callback
def configured_devices(hass):
    """return a set of all configured instances"""
    configuered_devices = list()
    for entry in hass.config_entries.async_entries(DOMAIN):
        configuered_devices.append(
            slugify_entry(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
        )
    return configuered_devices


@callback
def initialized_devices(hass):
    """return a set of all initialized instances"""
    initialized_devices = list()
    for slug in hass.data.get(DOMAIN, {}).keys():
        initialized_devices.append(slug)
    return initialized_devices


class DigitalStromFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """handle a digitalSTROM config flow"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    discovered_devices = []

    def __init__(self):
        self.device_config = {
            CONF_HOST: DEFAULT_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_USERNAME: DEFAULT_USERNAME,
            CONF_PASSWORD: "",
            CONF_ALIAS: DEFAULT_ALIAS,
        }

    async def async_step_user(self, user_input=None):
        """handle the start of the config flow"""
        errors = {}

        # validate input
        if user_input is not None:
            from pydigitalstrom.client import DSClient
            from pydigitalstrom.exceptions import DSException

            # build client config
            self.device_config = user_input.copy()

            # get device identifier slug
            device_slug = slugify_entry(
                host=self.device_config[CONF_HOST], port=self.device_config[CONF_PORT]
            )

            # check if server is already known
            if device_slug in configured_devices(self.hass):
                errors["base"] = "already_configured"
            else:
                # try to get an app token from the server and register it
                client = DSClient(
                    host=HOST_FORMAT.format(
                        host=self.device_config[CONF_HOST],
                        port=self.device_config[CONF_PORT],
                    ),
                    username=self.device_config[CONF_USERNAME],
                    password=self.device_config[CONF_PASSWORD],
                    config_path=self.hass.config.path(
                        CONFIG_PATH.format(host=user_input[CONF_HOST])
                    ),
                    apartment_name=self.device_config[CONF_ALIAS],
                )
                try:
                    await client.get_application_token()
                except DSException:
                    errors["base"] = "communication_error"
                else:
                    return self.async_create_entry(
                        title=TITLE_FORMAT.format(
                            alias=self.device_config[CONF_ALIAS],
                            host=self.device_config[CONF_HOST],
                            port=self.device_config[CONF_PORT],
                        ),
                        data=self.device_config,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.device_config[CONF_HOST]): str,
                    vol.Required(CONF_PORT, default=self.device_config[CONF_PORT]): int,
                    vol.Required(
                        CONF_USERNAME, default=self.device_config[CONF_USERNAME]
                    ): str,
                    vol.Required(
                        CONF_PASSWORD, default=self.device_config[CONF_PASSWORD]
                    ): str,
                    vol.Required(
                        CONF_ALIAS, default=self.device_config[CONF_ALIAS]
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_ssdp(self, discovery_info):
        """
        Handle a discovered digitalSTROM server.
        
        This will prefill the device data and redirect to the user form
        to check and complete information.
        """

        # something that is not a digitalSTROM server has been discovered
        if discovery_info.get(ATTR_MANUFACTURER) not in DIGITALSTROM_MANUFACTURERS:
            return self.async_abort(reason="not_digitalstrom_server")

        # device already known, filter duplicates
        device_slug = slugify_entry(
            host=discovery_info.get(ATTR_HOST), port=DEFAULT_PORT
        )
        if device_slug in initialized_devices(self.hass):
            return self.async_abort(reason="already_configured")

        # add to discovered devices
        if device_slug in self.discovered_devices:
            return self.async_abort(reason="already_discovered")
        self.discovered_devices.append(device_slug)

        # pre-fill schema and let the user complete it
        self.device_config = {
            CONF_HOST: discovery_info.get(ATTR_HOST),
            CONF_PORT: DEFAULT_PORT,
            CONF_USERNAME: DEFAULT_USERNAME,
            CONF_PASSWORD: "",
            CONF_ALIAS: discovery_info.get(ATTR_NAME),
        }
        return await self.async_step_user()

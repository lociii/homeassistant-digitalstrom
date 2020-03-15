"""Config flow to configure the digitalSTROM component."""
from urllib.parse import urlparse
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.ssdp import (
    ATTR_UPNP_MANUFACTURER,
    ATTR_SSDP_LOCATION,
    ATTR_UPNP_FRIENDLY_NAME,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ALIAS,
    CONF_TOKEN,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation

from .const import (
    DOMAIN,
    HOST_FORMAT,
    DIGITALSTROM_MANUFACTURERS,
    CONF_DELAY,
    DEFAULT_ALIAS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_DELAY,
    DEFAULT_USERNAME,
    TITLE_FORMAT,
    OPTION_GENERIC_SCENES,
    OPTION_GENERIC_SCENES_DEFAULT,
)
from .util import slugify_entry


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


class DigitalStromConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """handle a digitalSTROM config flow"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH
    discovered_devices = []

    def __init__(self, *args, **kwargs):
        self.device_config = {
            CONF_HOST: DEFAULT_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_USERNAME: DEFAULT_USERNAME,
            CONF_PASSWORD: "",
            CONF_ALIAS: DEFAULT_ALIAS,
            CONF_DELAY: DEFAULT_DELAY,
        }
        super().__init__(*args, **kwargs)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DigitalStromOptionsFlow(config_entry=config_entry)

    async def async_step_user(self, user_input=None):
        """handle the start of the config flow"""
        errors = {}

        # validate input
        if user_input is not None:
            from pydigitalstrom.apptokenhandler import DSAppTokenHandler
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
                handler = DSAppTokenHandler(
                    host=self.device_config[CONF_HOST],
                    port=self.device_config[CONF_PORT],
                    username=self.device_config[CONF_USERNAME],
                    password=self.device_config[CONF_PASSWORD],
                )
                try:
                    token = await handler.request_apptoken()
                except DSException:
                    errors["base"] = "communication_error"
                else:
                    return self.async_create_entry(
                        title=TITLE_FORMAT.format(
                            alias=self.device_config[CONF_ALIAS],
                            host=self.device_config[CONF_HOST],
                            port=self.device_config[CONF_PORT],
                        ),
                        data={
                            CONF_TOKEN: token,
                            CONF_HOST: self.device_config[CONF_HOST],
                            CONF_PORT: self.device_config[CONF_PORT],
                            CONF_ALIAS: self.device_config[CONF_ALIAS],
                            CONF_DELAY: self.device_config[CONF_DELAY],
                        },
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
                    vol.Required(
                        CONF_DELAY, default=self.device_config[CONF_DELAY]
                    ): int,
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
        if discovery_info.get(ATTR_UPNP_MANUFACTURER) not in DIGITALSTROM_MANUFACTURERS:
            return self.async_abort(reason="not_digitalstrom_server")

        # get host from ssdp location
        parseresult = urlparse(discovery_info.get(ATTR_SSDP_LOCATION))
        host = str(parseresult.netloc)
        # cut off the port since it's not the expected one anyway
        if ":" in host:
            host, _port = host.split(":")

        # device already known, filter duplicates
        device_slug = slugify_entry(host=host, port=DEFAULT_PORT)
        if device_slug in initialized_devices(self.hass):
            return self.async_abort(reason="already_configured")

        # add to discovered devices
        if device_slug in self.discovered_devices:
            return self.async_abort(reason="already_discovered")
        self.discovered_devices.append(device_slug)

        # pre-fill schema and let the user complete it
        self.device_config = {
            CONF_HOST: host,
            CONF_PORT: DEFAULT_PORT,
            CONF_USERNAME: DEFAULT_USERNAME,
            CONF_PASSWORD: "",
            CONF_ALIAS: discovery_info.get(ATTR_UPNP_FRIENDLY_NAME),
            CONF_DELAY: DEFAULT_DELAY,
        }
        return await self.async_step_user()


class DigitalStromOptionsFlow(config_entries.OptionsFlow):
    """Handle a option flow for DigitalStrom."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        from pydigitalstrom import constants

        # build scene list for mutli select
        scenes = {}
        for scene_id, scene_name in constants.SCENE_NAMES.items():
            scenes[scene_name] = scene_name
        scenes = sorted(scenes)

        # build options based on multi select
        options = {
            vol.Optional(
                OPTION_GENERIC_SCENES,
                default=self.config_entry.options.get(
                    OPTION_GENERIC_SCENES, OPTION_GENERIC_SCENES_DEFAULT
                ),
            ): config_validation.multi_select(scenes),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))

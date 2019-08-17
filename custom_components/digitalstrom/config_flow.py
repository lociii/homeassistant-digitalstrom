"""Config flow to configure the digitalSTROM component."""
import os

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.ssdp import (
    ATTR_MANUFACTURER, ATTR_HOST, ATTR_NAME)
from homeassistant.const import (
    CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, CONF_ACCESS_TOKEN,
    CONF_ALIAS)
from homeassistant.core import callback
from homeassistant.util import slugify

from .const import (
    DOMAIN, CONFIG_PATH, HOST_FORMAT, DIGITALSTROM_MANUFACTURERS, DEFAULT_HOST,
    DEFAULT_PORT, DEFAULT_USERNAME, DEFAULT_ALIAS, CONF_SLUG, SLUG_FORMAT,
    TITLE_FORMAT)
from .errors import AlreadyConfigured, CannotConnect


@callback
def configured_devices(hass):
    """return a set of all configured instances"""
    return {entry.data[CONF_SLUG]: entry for entry
            in hass.config_entries.async_entries(DOMAIN)}


@callback
def initialized_devices(hass):
    """return a set of all initialized instances"""
    return {
        slugify(SLUG_FORMAT.format(
            host=device[CONF_HOST], port=device[CONF_PORT])): device for device
        in hass.data.get(DOMAIN, {}).values()}


@config_entries.HANDLERS.register(DOMAIN)
class DigitalStromFlowHandler(config_entries.ConfigFlow):
    """handle a digitalSTROM config flow"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the digitalSTROM config flow."""
        self.device_config = {}
        self.discovery_schema = {}
        self.import_schema = {}

    async def async_step_init(self, user_input=None):
        """needed in order to not require re-translation of strings"""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """handle the start of the config flow"""
        errors = {}

        if user_input is not None:
            from pydigitalstrom.client import DSClient
            from pydigitalstrom.exceptions import DSException

            # build client config
            self.device_config = user_input.copy()

            # server already known
            if self.device_config[CONF_SLUG] in configured_devices(self.hass):
                raise AlreadyConfigured

            # try to get an app token from the server and register it
            try:
                client = DSClient(
                    host=HOST_FORMAT.format(
                        host=self.device_config[CONF_HOST],
                        port=self.device_config[CONF_PORT]),
                    username=self.device_config[CONF_USERNAME],
                    password=self.device_config[CONF_PASSWORD],
                    config_path=self.hass.config.path(
                        CONFIG_PATH.format(host=user_input[CONF_HOST])),
                    apartment_name=self.device_config[CONF_ALIAS])
                try:
                    apptoken = await client.get_application_token()
                except DSException:
                    raise CannotConnect

                # add apptoken to device config
                self.device_config[CONF_ACCESS_TOKEN] = apptoken

                return await self._create_entry()   
            except AlreadyConfigured:
                errors['base'] = 'already_configured'

            except CannotConnect:
                errors['base'] = 'communication_error'

        data = self.import_schema or self.discovery_schema or {
            vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_ALIAS, default=DEFAULT_ALIAS): str,
        }

        return self.async_show_form(
            step_id='user',
            description_placeholders=self.device_config,
            data_schema=vol.Schema(data),
            errors=errors
        )

    async def _create_entry(self):
        """create entry for instance"""

        # add slug to device config
        self.device_config[CONF_SLUG] = slugify(SLUG_FORMAT.format(
            host=self.device_config[CONF_HOST],
            port=self.device_config[CONF_PORT]))

        return self.async_create_entry(
            title=TITLE_FORMAT.format(host=self.device_config[CONF_HOST]),
            data=self.device_config)

    async def _update_entry(self, entry, host):
        """update existing entry"""
        entry.data[CONF_HOST] = host
        self.hass.config_entries.async_update_entry(entry)

    async def async_step_ssdp(self, discovery_info):
        """Handle a discovered digitalSTROM server."""

        # something that is not a digitalSTROM server has been discovered
        if discovery_info[ATTR_MANUFACTURER] not in DIGITALSTROM_MANUFACTURERS:
            return self.async_abort(reason='not_digitalstrom_server')

        # device already known
        slug = slugify(SLUG_FORMAT.format(
            host=discovery_info[ATTR_HOST], port=DEFAULT_PORT))
        if slug in initialized_devices(self.hass):
            return self.async_abort(reason='already_configured')

        # pre-fill schema and let the user complete it
        self.discovery_schema = {
            vol.Required(CONF_HOST, default=discovery_info[ATTR_HOST]): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_ALIAS, default=discovery_info[ATTR_NAME]): str,
        }
        return await self.async_step_user()

    async def async_step_import(self, import_config):
        """Import a digitalSTROM server as a config entry.

        This flow is triggered by `async_setup` for configured servers.
        This flow is also triggered by `async_step_discovery`.

        This will execute for any server that does not have a
        config entry yet (based on host).

        If the apptoken file exists, we will create an entry.
        Otherwise we will delegate to `link` step which
        will ask user to link the server.
        """
        self.device_config = import_config
        # no apptoken in device config
        if 'apptoken' not in self.device_config:
            return await self.async_step_link()

        return await self._create_entry()

    async def async_step_link(self):
        from pydigitalstrom.client import DSClient
        from pydigitalstrom.exceptions import DSException

        # try to get an app token from the server and register it
        try:
            client = DSClient(
                host=HOST_FORMAT.format(
                    host=self.device_config[CONF_HOST],
                    port=self.device_config[CONF_PORT]),
                username=self.device_config[CONF_USERNAME],
                password=self.device_config[CONF_PASSWORD],
                config_path=self.hass.config.path(
                    CONFIG_PATH.format(
                        host=self.device_config[CONF_HOST])),
                apartment_name=self.device_config[CONF_ALIAS])
            try:
                apptoken = await client.get_application_token()
            except DSException:
                raise CannotConnect

            # add apptoken to device config
            self.device_config[CONF_ACCESS_TOKEN] = apptoken

            return await self._create_entry()   
        except AlreadyConfigured:
            reason = 'already_configured'

        except CannotConnect:
            reason = 'communication_error'

        return self.async_abort(reason=reason)

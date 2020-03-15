# -*- coding: UTF-8 -*-
import logging
from typing import Callable, Union

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from pydigitalstrom import constants
from pydigitalstrom.client import DSClient
from pydigitalstrom.devices.scene import DSScene, DSColorScene

from .const import DOMAIN
from .util import slugify_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_devices: Callable,
    discovery_info: dict = None,
):
    """Platform uses config entry setup."""
    pass


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities: Callable
) -> None:
    entry_slug: str = slugify_entry(
        host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]
    )

    client: DSClient = hass.data[DOMAIN][entry_slug]["client"]
    scenes: list = []

    scene: Union[DSScene, DSColorScene]
    for scene in client.get_scenes().values():
        # only color scenes have a special check
        if isinstance(scene, DSColorScene):
            # area and broadcast scenes (yellow/1 and grey/2 up to id 9)
            # shouldn't be added since they'll be processed as
            # lights and covers
            if scene.color in (1, 2) and scene.scene_id <= 9:
                continue

        _LOGGER.info(f"adding scene {scene.scene_id}: {scene.name}")
        scenes.append(DigitalstromScene(scene=scene, config_entry=entry))

    scene: DigitalstromScene
    async_add_entities(scene for scene in scenes)


class DigitalstromScene(Scene):
    """Representation of a digitalSTROM scene."""

    def __init__(
        self,
        scene: Union[DSScene, DSColorScene],
        config_entry: ConfigEntry,
        *args,
        **kwargs,
    ):
        self._scene: Union[DSScene, DSColorScene] = scene
        self._config_entry: ConfigEntry = config_entry
        super().__init__(*args, **kwargs)

    @property
    def name(self) -> str:
        return self._scene.name

    @property
    def unique_id(self) -> str:
        return f"dsscene_{self._scene.unique_id}"

    async def async_activate(self) -> None:
        _LOGGER.info(f"calling scene {self._scene.scene_id}")
        await self._scene.turn_on()

    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self) -> dict:
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self._scene.unique_id)},
            "name": self._scene.name,
            "model": "DSScene",
            "manufacturer": "digitalSTROM AG",
        }

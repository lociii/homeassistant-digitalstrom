# -*- coding: UTF-8 -*-
import logging
from typing import Callable, Union

from homeassistant.components.cover import CoverDevice, SUPPORT_CLOSE, SUPPORT_OPEN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from pydigitalstrom.client import DSClient
from pydigitalstrom.devices.scene import DSScene, DSColorScene
from pydigitalstrom.websocket import DSWebsocketEventListener

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
    entry_slug: str = slugify_entry(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])

    client: DSClient = hass.data[DOMAIN][entry_slug]["client"]
    listener: DSWebsocketEventListener = hass.data[DOMAIN][entry_slug]["listener"]
    devices: list = []
    scenes: dict = client.get_scenes()

    scene: Union[DSScene, DSColorScene]
    for scene in scenes.values():
        # only handle cover (color 2) scenes
        if not isinstance(scene, DSColorScene) or scene.color != 2:
            continue
        # not an area or broadcast turn off scene
        if scene.scene_id > 4:
            continue

        # get turn on counterpart
        scene_on: DSColorScene = scenes.get(
            f"{scene.zone_id}_{scene.color}_{scene.scene_id + 5}", None
        )

        # no turn on scene found, skip
        if not scene_on:
            continue

        # add cover
        _LOGGER.info(f"adding cover {scene.scene_id}: {scene.name}")
        devices.append(
            DigitalstromCover(
                hass=hass, scene_on=scene_on, scene_off=scene, listener=listener
            )
        )

    device: DigitalstromCover
    async_add_entities(device for device in devices)


class DigitalstromCover(CoverDevice):
    def __init__(
        self,
        hass: HomeAssistantType,
        scene_on: DSColorScene,
        scene_off: DSColorScene,
        listener: DSWebsocketEventListener,
        *args,
        **kwargs,
    ):
        self._hass: HomeAssistantType = hass
        self._scene_on: DSColorScene = scene_on
        self._scene_off: DSColorScene = scene_off
        self._listener: DSWebsocketEventListener = listener
        self._state: bool = None
        super().__init__(*args, **kwargs)

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE

    @property
    def name(self) -> str:
        return self._scene_off.name

    @property
    def unique_id(self) -> str:
        return f"dscover_{self._scene_off.unique_id}"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_closed(self) -> bool:
        return None

    async def async_open_cover(self, **kwargs) -> None:
        _LOGGER.info(f"calling cover scene {self._scene_on.scene_id}")
        await self._scene_on.turn_on()

    async def async_close_cover(self, **kwargs) -> None:
        _LOGGER.info(f"calling cover scene {self._scene_off.scene_id}")
        await self._scene_off.turn_on()

    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self) -> dict:
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self._scene_off.unique_id)},
            "name": self._scene_off.name,
            "model": "DSCover",
            "manufacturer": "digitalSTROM AG",
        }

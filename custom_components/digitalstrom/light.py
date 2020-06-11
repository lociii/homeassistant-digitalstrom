# -*- coding: UTF-8 -*-
import logging
from typing import Callable, Union

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, CONF_HOST, CONF_PORT
from homeassistant.helpers.restore_state import RestoreEntity
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
    entry_slug: str = slugify_entry(
        host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]
    )

    client: DSClient = hass.data[DOMAIN][entry_slug]["client"]
    listener: DSWebsocketEventListener = hass.data[DOMAIN][entry_slug]["listener"]
    devices: dict = []
    scenes: dict = client.get_scenes()

    scene: Union[DSScene, DSColorScene]
    for scene in scenes.values():
        # only handle light (color 1) scenes
        if not isinstance(scene, DSColorScene) or scene.color != 1:
            continue
        # not an area or broadcast turn off scene
        if scene.scene_id > 4:
            continue

        # get turn on counterpart
        scene_on: Union[DSScene, DSColorScene] = scenes.get(
            f"{scene.zone_id}_{scene.color}_{scene.scene_id + 5}", None,
        )

        # no turn on scene found, skip
        if not scene_on:
            continue

        # add light
        _LOGGER.info(f"adding light {scene.scene_id}: {scene.name}")
        devices.append(
            DigitalstromLight(
                hass=hass, scene_on=scene_on, scene_off=scene, listener=listener
            )
        )

    device: DigitalstromLight
    async_add_entities(device for device in devices)


class DigitalstromLight(RestoreEntity, LightEntity):
    def __init__(
        self,
        hass: HomeAssistantType,
        scene_on: Union[DSScene, DSColorScene],
        scene_off: Union[DSScene, DSColorScene],
        listener: DSWebsocketEventListener,
        *args,
        **kwargs,
    ):
        self._hass: HomeAssistantType = hass
        self._scene_on: Union[DSScene, DSColorScene] = scene_on
        self._scene_off: Union[DSScene, DSColorScene] = scene_off
        self._listener: DSWebsocketEventListener = listener
        self._state: bool = None
        super().__init__(*args, **kwargs)

        self.register_callback()

    def register_callback(self):
        async def event_callback(event: dict) -> None:
            # sanity checks
            if "name" not in event:
                return
            if event["name"] != "callScene":
                return
            if "properties" not in event:
                return
            if "sceneID" not in event["properties"]:
                return
            if "groupID" not in event["properties"]:
                return
            if "zoneID" not in event["properties"]:
                return

            # cast event data
            zone_id: int = int(event["properties"]["zoneID"])
            group_id: int = int(event["properties"]["groupID"])
            scene_id: int = int(event["properties"]["sceneID"])

            # device turned on or broadcast turned on
            if (
                self._scene_on.zone_id == zone_id
                and self._scene_on.color == group_id
                and (self._scene_on.scene_id == scene_id or 5 == scene_id)
            ):
                self._state = True
                await self.async_update_ha_state()
            # device turned off or broadcast turned off
            elif (
                self._scene_off.zone_id == zone_id
                and self._scene_off.color == group_id
                and (self._scene_off.scene_id == scene_id or 0 == scene_id)
            ):
                self._state = False
                await self.async_update_ha_state()

        self._listener.register(callback=event_callback)

    @property
    def name(self) -> str:
        return self._scene_off.name

    @property
    def unique_id(self) -> str:
        return f"dslight_{self._scene_off.unique_id}"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self._state

    async def async_turn_on(self, **kwargs) -> None:
        await self._scene_on.turn_on()
        self._state = True

    async def async_turn_off(self, **kwargs) -> None:
        await self._scene_off.turn_on()
        self._state = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state: bool = await self.async_get_last_state()
        if not state:
            return

        _LOGGER.debug(
            f"trying to restore state of entity {self.entity_id} to {state.state}"
        )
        self._state = state.state == STATE_ON

    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self) -> dict:
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self._scene_off.unique_id)},
            "name": self._scene_off.name,
            "model": "DSLight",
            "manufacturer": "digitalSTROM AG",
        }

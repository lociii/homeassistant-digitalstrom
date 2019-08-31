# digitalSTROM component for Home Assistant

This integration makes digitalSTROM lights, covers, switches and scenes available in Home Assistant.

It supports config flows so that you can easily add your digitalSTROM server from the Home Assistant frontend (Configuration -> Integrations).

However it does not support YAML config setup (anymore). The future is the frontend!

## digitalSTROM basics

The digitalSTROM state machine works best when devices are not controlled directly. Therefore this integration works exclusively with the concept of digitalSTROM scenes. However to be more convenient, some scenes are combined to form meta devices.

## Lights

These are not real lights! e.g. no GE-KM200 or similar is exposed directly.
Instead the activation and deactivation scenes of digitalSTROM light areas are combined to light devices.
Each room consists of four areas and a broadcast (all on/off). The name of the turn-off-scene is used as the device name,

## Covers

Same behavior as with lights for area cover scenes

## Switches

Only sleeping and presence on/off scenes are merged in meta switch devices for now.

## Scenes

Every scene that is not an area light or cover scene is exposed as a regular scene to Home Assistant.

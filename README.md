# digitalSTROM component for Home Assistant

## What is this about?

[Home Assistant](https://www.home-assistant.io/) is an open source home automation and control system.

[digitalSTROM](https://www.digitalstrom.com/) is a smart home control solution developed by the Swiss digitalSTROM AG

## What does it do?

This integration makes digitalSTROM lights, covers, switches and scenes available in Home Assistant.

It supports config flows (and would support SSDP discovery if it was available to custom components) so that you can easily add your digitalSTROM server from the Home Assistant frontend (Configuration -> Integrations).

However it does not support YAML config setup (anymore). The future is the frontend!

### digitalSTROM basics

The digitalSTROM state machine works best when devices are not controlled directly. Therefore this integration works exclusively with the concept of digitalSTROM scenes. However to be more convenient, some scenes are combined to form meta devices.

### Lights

These are not real lights! e.g. no GE-KM200 or similar is exposed directly.
Instead the activation and deactivation scenes of digitalSTROM light areas are combined to light devices.
Each room consists of four areas and a broadcast (all on/off). The name of the turn-off-scene is used as the device name,

### Covers

Same behavior as with lights for area cover scenes

### Switches

Only sleeping and presence on/off scenes are merged in meta switch devices for now.

### Scenes

Every scene that is not an area light or cover scene is exposed as a regular scene to Home Assistant.

## How can I install it?

The easiest way to install the integration is by using [Home Assistant Community Store HACS](https://hacs.netlify.com/).
For now, you have to [add the repository yourself](https://hacs.netlify.com/usage/settings/#add-custom-repositories) - chose type "Integration".

## Are there any limitations?

Yes. Based on the nature of how digitalSTROM servers communicate with single devices, a digitalSTROM installation can easily be overwhelmed with too many commands. It is therefore recommended to not issue more than 2-3 commands per second.

Future versions of this integration might add a delaying queue to protect your installation.

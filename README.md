# digitalSTROM component for Home Assistant

## What is this about?

[Home Assistant](https://www.home-assistant.io/) is an open source home automation and control system.

[digitalSTROM](https://www.digitalstrom.com/) is a smart home control solution developed by the Swiss digitalSTROM AG

## What does it do?

This integration makes digitalSTROM lights, covers, switches and scenes available in Home Assistant.

It supports config flows (and would support SSDP discovery if it was available to custom components) so that you can easily add your digitalSTROM server from the Home Assistant frontend (Configuration -> Integrations).

However it does not support YAML config setup (anymore). The future is the frontend!

Please read [info.md](info.md) carefully to understand how this integration works with digitalSTROM features and why devices cannot be controlled directly.

## How can I install it?

The easiest way to install the integration is by using [Home Assistant Community Store HACS](https://hacs.netlify.com/).
For now, you have to [add the repository yourself](https://hacs.netlify.com/usage/settings/#add-custom-repositories) - chose type "Integration".

## Are there any limitations?

Yes. Based on the nature of how digitalSTROM servers communicate with single devices, a digitalSTROM installation can easily be overwhelmed with too many commands. It is therefore recommended to not issue more than 2-3 commands per second.

Future versions of this integration might add a delaying queue to protect your installation.

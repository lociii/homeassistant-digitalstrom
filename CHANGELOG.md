# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changes
- Type annotate everything
- Simplify storage of DSClient and DSWebsocketEventListener
- Add options flow to hide unwanted generic scenes like rain or hail

## [1.2.0] - 2020-01-16
### Changed
- Support for HA below 0.104 removed (caused by changes in SSDP discovery)
- Updated pydigitalstrom (now depends on aiohttp 3.6.1 see https://github.com/aio-libs/aiohttp/issues/4258)

## [1.1.0] - 2019-09-01
### Changed
- BREAKING - application token will not be stored in a file anymore but in the config entry
  integration must be reset and freshly added again

## [1.0.0] - 2019-08-31
### Changed
- initial public release

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.14] - 2026-07-21

### Added
- `reader_id` and `reader_name` attributes on Door Event entities, identifying which physical reader processed the event. Only present when the controller reports reader data.

### Fixed
- `guard_ids` now correctly appears on doorbell events for UA-Intercom + separate lock hub topologies (e.g. UA-Intercom paired with UA-Hub-Door-Mini). The check now uses the event payload's `device_type` instead of the door's registered hub type.

## [3.0.13] - 2026-07-20

### Added
- `stop` action for UGT gate and garage door cover entities. Open, close, and stop now send the corresponding motor command (`control_cmd=open|close|stop`) directly to the UGT hub.

## [3.0.12] - 2026-07-19

### Added
- `Face Unlock` switch entity (`switch.<door>_face_unlock`) for readers that report face unlock capability (e.g. UA-Intercom). The switch enables or disables biometric face unlock per door and is only created for capable devices. State is fetched at startup and updated optimistically on toggle; polling mode refreshes it on each cycle. Requires `py-unifi-access==1.6.1`.

## [3.0.11] - 2026-07-17

### Fixed
- User management actions (`enable_user`, `disable_user`, `update_user_pin`) now work correctly. The underlying `py-unifi-access` library was using the wrong HTTP method (`PATCH`) and wrong status values (`active`/`inactive`) — the UniFi Access API only supports `GET`/`POST`/`PUT`/`DELETE`, and status values are `ACTIVE`/`DEACTIVATED`. The `update_user_pin` action was also sending to the wrong endpoint; it now uses `PUT /users/:id/pin_codes` to assign and `DELETE /users/:id/pin_codes` to remove. Requires `py-unifi-access==1.6.1`.

## [3.0.10] - 2026-07-17

### Fixed
- Bump `py-unifi-access` requirement to 1.5.0. Version 1.4.0 was never published to PyPI due to a CI race condition (two PRs merged simultaneously cancelled the publish job), making 3.0.9 uninstallable.

## [3.0.9] - 2026-07-17

### Added
- Three user management actions: `enable_user`, `disable_user`, and `update_user_pin`. These are domain-level actions (not per-door) that let you enable/disable a user's access or update their PIN from automations or Developer Tools.

## [3.0.8] - 2026-07-12

### Fixed
- Added support for standard `'ring'` event type for doorbell event entities to resolve Home Assistant 2027.4 compatibility warnings (#217).
- Preserved backward compatibility by continuing to trigger legacy `unifi_access_doorbell_start` and `unifi_access_doorbell_stop` events.
- Updated all translation files and added automated unit tests for doorbell events.

## [3.0.7] - 2026-06-08

### Added
- Full Unicode support for device names with special characters (ö, ä, ü, etc.)
- Support for Unifi Access G3 Intercom (UA-G3-Intercom)
- Unicode NFC normalization for consistent door name handling
- Fixed doorbell event detection for devices with special character names

### Fixed
- Unicode door name matching issues that prevented doorbell events from being detected
- WebSocket event matching for devices with German umlauts and other special characters

### Changed
- Improved international character support for German, French, and other languages

## [3.0.6] - 2026-05-17

### Fixed
- Updated `py-unifi-access` to 1.2.0 to handle websocket device update payloads where `category` can be `null`

## [1.3.2] - 2024-10-21

### Changed
- Testing new event behavior
- Documentation updates

## [1.3.1] - 2024-10-21

### Changed
- Updated manifest version
- Documentation improvements

## [1.3.0] - 2024-09-15

### Added
- Door entry/exit result information in event attributes
- Device door association improvements

### Changed
- Updated async entry types for better compatibility

## [1.2.9] - 2024-08-12

### Added
- Better error handling for thumbnails
- Stale entity removal functionality

### Fixed
- Polling issues
- Thumbnail retrieval errors

## [1.2.8] - 2024-07-28

### Fixed
- DPS (Door Position Sensor) handling improvements
- Lock rule logic corrections
- Issues with UA-ULTRA devices (#96)

### Changed
- Version bumping process

## [1.2.7] - 2024-06-15

### Added
- Thumbnail support for door events
- Support for additional hub types
- Updated documentation links

### Changed
- Improved datetime handling
- Better hub compatibility

## [1.2.6] - 2024-05-20

### Added
- Interface device filtering (ignore interface devices)

### Fixed
- Restored missing credential provider functionality
- Small compatibility improvements

## [1.2.5] - 2024-04-18

### Added
- Chinese (Simplified) translation support

### Changed
- Updated manifest version

## [1.2.4] - 2024-03-25

### Added
- Basic support for UA-Intercom devices
- Credential Provider information for access.logs.add events
- Improved logging functionality

### Changed
- Updated README with new device support

## [1.2.3] - 2024-02-28

### Added
- Support for UAH-DOOR device type
- Default handler for unknown hub types
- Better error messages for unsupported devices

### Fixed
- Issue templates updated
- Documentation type corrections

## [1.2.2] - 2024-02-15

### Added
- Support for multiple doors on single update messages
- German (de) translation
- Italian (it) translation
- Dutch (nl) translation

### Changed
- Improved multi-door handling logic
- Code comments and documentation

## [1.2.1] - 2024-01-20

### Added
- Translation support infrastructure
- Multiple language files

## [1.2.0] - 2024-01-10

### Added
- Evacuation and lockdown functionality
- Temporary lock rules support
- Support for UGT (Unifi Gate Hub) devices
- Support for UAH-Ent (Enterprise) devices
- Support for UA-ULTRA devices
- GitHub Actions workflow
- Translation keys system

### Fixed
- Coordinator performance improvements
- Door lock rule support detection
- KeyError exception handling

### Changed
- Manifest file organization (alphabetical sorting)
- Documentation updates

## [1.1.6] - 2023-11-15

### Changed
- Version number update

## [1.1.5] - 2023-11-10

### Changed
- Updated manifest version
- Updated requests and websocket-client library versions

### Added
- Hardware doorbell support
- Instant updates via WebSocket
- Configuration cleanup

## [1.1.4] - 2023-10-25

### Added
- Support for OPEN door events
- Code refactoring for better maintainability

## [1.1.3] - 2023-10-15

### Added
- Event system implementation
- Access and doorbell press events
- Event metadata (door_name, door_id, type, authentication, actor)

### Fixed
- Potential threading issues
- Unused variable cleanup

### Changed
- README documentation improvements

## [1.1.2] - 2023-09-28

### Fixed
- Doorbell press variable assignment issues

## [1.1.1] - 2023-09-20

### Added
- Automatic WebSocket reconnection on connection close
- 5-second retry interval for reconnections

### Fixed
- Connection stability improvements

## [1.1.0] - 2023-09-10

### Added
- WebSocket support for real-time updates
- Doorbell status as boolean sensor
- String localization support

### Changed
- Moved from polling to WebSocket-based updates
- Improved real-time responsiveness

## [1.0.3] - 2023-08-25

### Fixed
- Only add doors when `is_bind_hub` is True
- Improved hub binding logic

## [1.0.2] - 2023-08-15

### Added
- Support for custom ports in configuration

## [1.0.1] - 2023-08-10

### Added
- SSL certificate verification option
- Configurable SSL handling

### Changed
- README documentation updates

## [1.0.0] - 2023-08-01

### Added
- Initial release
- Basic Unifi Access integration
- Door lock/unlock functionality
- Door position sensors
- Configuration flow setup
- Support for UAH (Unifi Access Hub)
- HACS integration
- Basic documentation

### Features
- Door control via Home Assistant interface
- Door position monitoring
- API token-based authentication
- SSL certificate handling options

---

## Legend

- **Added** - New features
- **Changed** - Changes in existing functionality  
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes

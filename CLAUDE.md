# hass-unifi-access

Home Assistant custom integration for UniFi Access. Uses `py-unifi-access` as the API library.

## Virtual environment

```bash
.venv/bin/python         # Python 3.14
.venv/bin/python -m pip  # package management
```

To use a local (dev) build of py-unifi-access:

```bash
.venv/bin/pip install -e /Users/anis/Documents/Projects/py-unifi-access
```

## Validation loop

```bash
.venv/bin/python -m pytest tests/ -v
```

That's the full loop for hass. No pre-commit/mypy setup in this repo.

## Integration layout

```
custom_components/unifi_access/
  __init__.py        # async_setup() for domain services; async_setup_entry() for entry setup
  hub.py             # UnifiAccessHub — door state, WS events, API calls
  coordinator.py     # UnifiAccessCoordinator — polling-mode DataUpdateCoordinator
  entity.py          # UnifiAccessDoorEntity base; manage_door_entities helper
  config_flow.py     # Config flow UI
  const.py           # Domain constants and door type strings
  binary_sensor.py   # Door position, lock status sensors
  button.py          # Unlock button
  cover.py           # UGT gate/garage cover (open/close/stop)
  event.py           # Doorbell / access entry event entities
  image.py           # Doorbell snapshot image
  lock.py            # Door lock entity
  number.py          # Lock rule interval
  select.py          # Lock rule type selector
  sensor.py          # Door state sensors
  switch.py          # Emergency evacuation/lockdown + FaceUnlockSwitch
  services.yaml      # Service UI metadata (fields, descriptions)
  strings.json       # Entity/service translation strings
  manifest.json      # Integration metadata, py-unifi-access version pin
```

## Data flow

```
async_setup_entry()
  → UnifiAccessHub(client)       # wraps API client
  → UnifiAccessCoordinator       # polls hub in polling mode
  → UnifiAccessData(hub, coordinator, emergency_coordinator, store)
       stored in entry.runtime_data
```

## DoorState (hub.py)

`DoorState` is a mutable dataclass stored in `hub.doors: dict[str, DoorState]` keyed by `door.id`.

Key fields:
- `door: Door` — immutable API model
- `hub_id: str | None` — device ID of the hub controlling this door
- `hub_type: str | None` — device type string (e.g. `"UGT"`, `"UA-Intercom"`)
- `entity_type: str` — `"door"` or `"cover"` (UGT)
- `lock_rule: str`, `lock_rule_ended_time: int`, `lock_rule_interval: int`
- `device_settings: DeviceSettings | None` — fetched for face-capable devices
- `has_face_unlock: bool` — True if hub device reports `support_face` capability

## Entities wired at setup

`manage_door_entities` (in `entity.py`) takes a predicate and factory and registers/deregisters entities as doors come and go:

```python
manage_door_entities(
    config_entry,
    coordinator,
    async_add_entities,
    predicate=lambda door: door.has_face_unlock,
    factory=lambda door_id: [FaceUnlockSwitch(data, door_id)],
)
```

Called in each platform's `async_setup_entry`. Doors that fail the predicate don't get entities.

## Domain services

Registered in `async_setup()` (not `async_setup_entry`) so they apply across all config entries:

- `enable_user` / `disable_user` / `update_user_pin` (user management)

Services use `ConfigEntrySelector` for `config_entry_id`. Schema defined in `__init__.py`, UI strings in `services.yaml` and `strings.json`.

## Hub methods added recently

```python
# UGT cover control (cover.py)
hub.async_open_door(door_id)   # control_cmd=open
hub.async_close_door(door_id)  # control_cmd=close
hub.async_stop_door(door_id)   # control_cmd=stop

# Face unlock (switch.py)
hub.async_set_face_unlock(door_id, enabled=True/False)  # PUT device settings + optimistic update
hub.async_refresh_device_settings()                      # re-fetch all face-capable doors
```

## Test patterns

```python
# Patch the API client at import time
with patch(
    "custom_components.unifi_access.UnifiAccessApiClient",
    return_value=mock_client,
):
    await hass.config_entries.async_setup(entry.entry_id)

# Domain setup (ConfigType is a type alias, not a class)
await async_setup(hass, {})

# Entity registry lookups
registry = er.async_get(hass)
entity_id = registry.async_get_entity_id("switch", DOMAIN, "door-001_face_unlock")
```

Sample data fixtures live in `tests/conftest.py`. Add new sample devices/settings there.

## Versions

| Version | Key changes |
|---------|-------------|
| 3.0.11  | FaceUnlockSwitch entity (requires py-unifi-access==1.6.0) |
| 3.0.10  | Bump to py-unifi-access==1.5.0 (1.4.0 was never published) |
| 3.0.9   | User management actions (enable/disable/update_pin) |
| 3.0.8   | Changelog / manifest housekeeping |
| 3.0.7   | UGT door type support |

## Active branches / PRs

- `fix/ugt-cover-stop` (PR #220) — UGT cover open/close/stop (requires py-unifi-access 1.5.0, merged)
- `feat/device-settings` (PR #222) — FaceUnlockSwitch entity (requires py-unifi-access 1.6.0)
- `feat/user-management` (PR #219, merged) — user management services

## Library dependency

`manifest.json` pins the exact py-unifi-access version. Always update it when bumping the library. The hass venv must have the matching version installed — install local dev builds with `pip install -e`.

## Creating a release

1. Update `CHANGELOG.md` — move items from `[Unreleased]` into a new dated version section.
2. Bump `"version"` in `manifest.json`.
3. Commit and push both files.
4. Create the GitHub release with `gh release create`.

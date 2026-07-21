# Unifi Access Custom Integration for Home Assistant

- This is a basic integration of [Unifi Access](https://ui.com/door-access) in [Home Assistant](https://homeassistant.io). 
- If you have Unifi Access set up with UID this will likely *NOT* work although some people have reported success using the free version of UID. 
- _Camera Feeds are currently not offered by the API and therefore **NOT** supported_.

## Table of Contents

- [Core integration vs. this HACS integration](#core-integration-vs-this-hacs-integration)
- [Supported hardware](#supported-hardware)
- [Getting Unifi Access API Token](#getting-unifi-access-api-token)
- [Installation (HACS)](#installation-hacs)
- [Installation (manual)](#installation-manual)
- [Events](#events)
  - [Doorbell Press](#doorbell-press)
  - [Door Event](#door-event)
  - [Evacuation/Lockdown](#evacuationlockdown)
  - [Thumbnail](#thumbnail)
  - [UGT garage door / gate support](#ugt-garage-door--gate-support)
  - [Face Unlock](#face-unlock-ua-intercom-and-other-face-capable-readers)
  - [Door lock rules](#door-lock-rules-only-applies-to-uah)
- [User Management Actions](#user-management-actions)
  - [Finding a user_id](#finding-a-user_id)
  - [enable_user](#unifi_accessenable_user)
  - [disable_user](#unifi_accessdisable_user)
  - [update_user_pin](#unifi_accessupdate_user_pin)
- [Example automations](#example-automations)
- [API Limitations](#api-limitations)
- [Removing the integration](#removing-the-integration)
- [Troubleshooting](#troubleshooting)
- [Support my work](#support-my-work)

## Core integration vs. this HACS integration

Home Assistant now includes a [core UniFi Access integration](https://www.home-assistant.io/integrations/unifi_access/). For most users, the core integration is the recommended starting point — it has met Home Assistant's Platinum quality requirements and is reviewed by core maintainers.

This HACS integration exists for users who need features that are not available in core, or that don't fit easily into the architectural rules required for Home Assistant core integrations.

**Use the core integration** if you want the most official, reviewed, and Home Assistant-native experience.  
**Use this HACS integration** if you specifically need one of the extras listed below.

### Feature comparison

| Feature | Core integration | This HACS integration |
|---|---|---|
| Door unlock | `button` entity | `lock` entity (unlock only; locking logs a warning) |
| Door position sensor | ✅ | ✅ |
| Doorbell event entity | ✅ | ✅ |
| Access event entity | ✅ | ✅ |
| Evacuation / Lockdown switches | ✅ | ✅ |
| Door lock rules (select + sensor) | ✅ (`set_lock_rule` action) | ✅ (select, number, and sensor entities) |
| Door thumbnail image | ✅ | ✅ |
| WebSocket push updates | ✅ | ✅ |
| Auto-discovery | ✅ | ❌ |
| Polling mode (for UA controller < 1.90) | ❌ | ✅ |
| UGT gate / garage door cover entities | ❌ | ✅ (open / close / stop) |
| UGT entity type selector (lock ↔ garage ↔ gate) | ❌ | ✅ (live swap, no restart needed) |
| Face Unlock switch (UA-Intercom) | ❌ | ✅ |
| User management actions (enable / disable / update PIN) | ❌ | ✅ |

# Supported hardware
- Unifi Access Hub (UAH) :white_check_mark:
- Unifi Access Hub (UAH-DOOR) :white_check_mark:
- Unifi Access Intercom (UA-Intercom) :white_check_mark:
- Unifi Access G3 Intercom (UA-G3-Intercom) :white_check_mark:
- Unifi Access Hub Enterprise (UAH-Ent) :white_check_mark:
- Unifi Gate Hub (UGT) :white_check_mark:
- Unifi Access Ultra (UA-Ultra) :white_check_mark:
- Unifi Access Door Mini (UA-Hub-Door-Mini) :white_check_mark:

# Getting Unifi Access API Token
- Go to http(s)://{unifi_access_console}/access/settings/system
- Create a new token and pick all permissions (this is *IMPORTANT*). At the very least pick: Space, Device and System Log.

# Installation (HACS)
- You can just add this integration to HACS by searching for Unifi Access. If you can't find it, follow the steps below.

- Add this repository as a custom repository in HACS and install the integration.
- Restart Home Assistant
- Add new Integration -> Unifi Access
- Enter your Unifi Access controller IP or Hostname (default is `unifi` or `UDMPRO`). No need to enter port or scheme
- Enter your API Token that you generated in Unifi Access
- Select `Verify SSL certificate` only if you have a valid SSL certificate. For example: If your Unifi Access API server is behind a reverse proxy. Selecting this will fail otherwise.
- Select `Use polling` if your Unifi Access version is < 1.90. Default is to use websockets for instantaneous updates and more features.
- It should find all of your doors and add the following entities for each one
    - Door Position Sensor (binary_sensor). If you don't have one connected, it will always be **off** (closed).
    - Doorbell (binary_sensor). Requires **Unifi Access Reader Pro G1/G2** otherwise always **off**. Only appears when **Use polling** is not selected.
    - Door Lock (lock). This is the default entity type for doors. You can unlock or open a door, but locking is unsupported and only logs a warning.
    - Thumbnail (`image`). Only appears when **Use polling** is not selected.
    - Event entities (`event`): Door Event and Doorbell Press. These are only created when `Use polling` is not selected.
    - For **UGT** doors: an `Entity Type` (`select`) entity lets you switch the door between `Lock (Door)`, `Garage Door`, and `Gate`.
    - When a UGT door is switched to `Garage Door` or `Gate`, the lock entity is replaced with:
        - a `cover` entity
        - `Opening Timeout` and `Closing Timeout` (`number`) helpers
        - a `Clear Obstruction` (`button`) helper
    - For **face-capable readers** (e.g. UA-Intercom): a `Face Unlock` (`switch`) entity to enable or disable biometric face unlock per door.


# Installation (manual)
- Clone this repository
- Copy the `custom_components/unifi_access` to your `config/custom_components` folder in Home Assistant.
- Restart Home Assistant
- Add new Integration -> Unifi Access
- Enter your Unifi Access controller IP or Hostname (default is `unifi` or `UDMPRO`). No need to enter port
- Enter your API Token that you generated in Unifi Access
- Select `Verify SSL certificate` only if you have a valid SSL certificate. For example: If your Unifi Access API server is behind a reverse proxy. Selecting this will fail otherwise.
- Select `Use polling` if your Unifi Access version is < 1.90. Default is to use websockets for instantaneous updates and more features.
- It should find all of your doors and add the following entities for each one
    - Door Position Sensor (binary_sensor). If you don't have one connected, it will always be **off** (closed).
    - Doorbell (binary_sensor). Requires **Unifi Access Reader Pro G1/G2** otherwise always **off**. Only appears when **Use polling** is not selected.
    - Door Lock (lock). This is the default entity type for doors. You can unlock or open a door, but locking is unsupported and only logs a warning.
    - Thumbnail (`image`). Only appears when **Use polling** is not selected.
    - Event entities (`event`): Door Event and Doorbell Press. These are only created when `Use polling` is not selected.
    - For **UGT** doors: an `Entity Type` (`select`) entity lets you switch the door between `Lock (Door)`, `Garage Door`, and `Gate`.
    - When a UGT door is switched to `Garage Door` or `Gate`, the lock entity is replaced with:
        - a `cover` entity
        - `Opening Timeout` and `Closing Timeout` (`number`) helpers
        - a `Clear Obstruction` (`button`) helper
    - For **face-capable readers** (e.g. UA-Intercom): a `Face Unlock` (`switch`) entity to enable or disable biometric face unlock per door.

# Events
When websocket mode is enabled (`Use polling` is **not** selected), this integration creates two Home Assistant `event` entities for each door:

- `Door Event`
- `Doorbell Press`

## Doorbell Press
One `Doorbell Press` entity is created per door. It updates when the integration receives a doorbell start or stop event.

### Event types
- `unifi_access_doorbell_start`
- `unifi_access_doorbell_stop`

### Event metadata
- `door_name`
- `door_id`
- `type`
- `guard_ids` (list of UUIDs) — IDs of the tenant/unit that rang the doorbell. **UA-Intercom only**, only present when non-empty. Cross-reference with the UniFi Access Users API to resolve to names.

> **Note:** `guard_ids` and other event metadata are carried on the HA event itself, not on the entity's state attributes. They are only visible in Developer Tools → Events (not States), and are accessed in automations via `trigger.event.data.guard_ids`. See the [example automation](#use-doorbell-guard-ids-in-an-automation) below.

For hardware doorbells, the integration may emit `unifi_access_doorbell_stop` automatically after a short delay if no explicit stop event is received.

## Door Event
One `Door Event` entity is created per door. It updates whenever the integration receives an access event for that door.

### Event types
- `unifi_access_entry`
- `unifi_access_exit`
- `unifi_access_access` (generic access event when the controller does not provide a clear entry/exit direction)

### Event metadata
- `door_name`
- `door_id`
- `actor` — the user tied to the event, when available
- `authentication` — authentication source reported by the controller
- `method` — opened method, when provided by the controller
- `type`
- `result` — examples: `ACCESS`, `BLOCKED`, `INCOMPLETE`
- `reader_id` — MAC address / device ID of the reader that processed the event. Only present when the controller reports reader data.
- `reader_name` — display name of that reader (e.g. `UA-G2-PRO-BB7A`). Only present when the controller reports reader data.

#### Warning regarding Door Events
Door events are using an undocumented API. Sadly, in September 2025, the Unifi Access API introduced some bugs that we have worked around but these events are still not 100% reliable depending on your hub. I recommend using the [Alarm Manager webhooks](https://github.com/imhotep/hass-unifi-access/issues/185#issuecomment-3895814140) if you need a more reliable way to automate based on door events.

### Evacuation/Lockdown
The evacuation (unlock all doors) and lockdown (lock all doors) switches apply to all doors and gates and **will sound the alarm** no matter which configuration you currently have in your terminal settings. The status will not update currently (known issue).

### Thumbnail 
A thumbnail of when the door is last accessed/locked/unlocked.

## UGT garage door / gate support

UGT doors can now be modeled per door as either:

- `Lock (Door)` - the default behavior
- `Garage Door`
- `Gate`

This is controlled by the `Entity Type` select created for UGT doors.

When you change that select:

- the choice is persisted for that door
- Home Assistant updates only the affected entities instead of reloading the full integration
- `Garage Door` and `Gate` create a `cover` entity with `open` / `close` / `stop` actions

For `Garage Door` and `Gate` cover mode, the integration also adds:

- `Opening Timeout` (`number`)
- `Closing Timeout` (`number`)
- `Clear Obstruction` (`button`)

Open, close, and stop send the corresponding motor command (`control_cmd=open|close|stop`) directly to the UGT hub. The timeout helpers let Home Assistant infer whether the door is still opening or closing and expose an `obstruction_detected` attribute when the sensor state does not match the expected result.

## Face Unlock (UA-Intercom and other face-capable readers)

For readers that report face unlock capability (e.g. UA-Intercom), the integration creates a `Face Unlock` switch entity per door:

- **Entity ID**: `switch.<door_name>_face_unlock`
- **Icon**: `mdi:face-recognition`
- **State**: reflects the current `access_methods.face.enabled` setting from the reader
- **Turn on**: enables biometric face unlock on that reader
- **Turn off**: disables biometric face unlock on that reader

The switch only appears for readers that support face unlock. Readers without this capability (e.g. standard UAH, UGT) will not have this entity.

State is fetched at startup and updated optimistically on toggle. In polling mode, the state is also refreshed on each poll cycle.

### Door lock rules (only applies to UAH)
The following entities will be created: `select`, `number` and 2 `sensor` entities (end time and current rule).
You are able to select one of the following rules via the `select` entity:
- **keep_lock**: door is locked indefinitely
- **keep_unlock**: door is unlocked indefinitely
- **custom**: door is unlocked for a given interval (use the `number` entity to define how long. Default is 10 minutes).
- **reset**: clear all lock rules
- **lock_early**: locks the door if it's currently on an unlock schedule.
- **lock_now**: locks the door if it's currently on an unlock schedule OR if it's unlocked temporarily via a locking rule.

# User Management Actions

Three actions let you manage user accounts directly from Home Assistant automations or Developer Tools. They are domain-level actions, not tied to any specific door.

## Finding a `user_id`

User IDs are UUIDs assigned by Unifi Access. You can find them in the Unifi Access web UI under **Users** (the ID appears in the URL when you open a user's profile), or from the Unifi Access API directly.

## `unifi_access.enable_user`

Enable a user's access credentials.

```yaml
action: unifi_access.enable_user
data:
  user_id: "abc123def456..."
```

## `unifi_access.disable_user`

Disable a user's access credentials without deleting them.

```yaml
action: unifi_access.disable_user
data:
  user_id: "abc123def456..."
```

## `unifi_access.update_user_pin`

Set or remove a user's PIN code. Omit `pin` (or leave it blank) to remove the existing PIN.

```yaml
# Set a PIN
action: unifi_access.update_user_pin
data:
  user_id: "abc123def456..."
  pin: "1234"
```

```yaml
# Remove the PIN
action: unifi_access.update_user_pin
data:
  user_id: "abc123def456..."
```

## Example: disable a user when a door is held open too long

```yaml
alias: Disable user on tailgate alarm
triggers:
  - platform: state
    entity_id: binary_sensor.front_door_door_position_sensor
    to: "on"
    for:
      minutes: 5
actions:
  - action: unifi_access.disable_user
    data:
      user_id: "abc123def456..."
mode: single
```

# Example automations

## Unlock door

```yaml
alias: Unlock Front Gate when motion is detected in Entryway
description: ""
trigger:
  - platform: state
    entity_id:
      - binary_sensor.entryway_motion_detected
condition: []
action:
  - service: lock.unlock
    data: {}
    target:
      device_id: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
mode: single
```

## Use doorbell guard IDs in an automation

`guard_ids` is available on the `unifi_access_doorbell_start` event (UA-Intercom only). Access it via `trigger.event.data` — it is not visible in the entity's state attributes.

```yaml
alias: Notify on doorbell ring with tenant ID
triggers:
  - platform: event
    event_type: unifi_access_doorbell_start
variables:
  door_name: "{{ trigger.event.data.door_name | default('Unknown door') }}"
  guard_ids: "{{ trigger.event.data.get('guard_ids', []) }}"
actions:
  - action: notify.mobile_app_my_phone
    data:
      title: Doorbell
      message: >
        {{ door_name }} rang.
        {% if guard_ids %}Tenant ID: {{ guard_ids | join(', ') }}.{% endif %}
mode: single
```

## Use event as automation trigger

Listen to Unifi Access events and use the event data to send a notification whenever someone accesses a door.

```yaml
alias: Announce person having opened a Unifi door
description: ""
triggers:
  - platform: event
    event_type: 
      - unifi_access_entry
      - unifi_access_access
variables:
  actor: "{{ trigger.event.data.actor or 'Unknown' }}"
  door_name: "{{ trigger.event.data.door_name or 'Unknown' }}"
actions:
  - action: notify.mobile_app_my_phone
    data:
      title: Door opened
      message: "{{ actor }} has opened {{ door_name }}."
mode: single
```
# API Limitations
The Unifi Access API does *NOT* support door locking at the moment. You probably already have it set to automatically lock after a small delay anyway.

# Removing the integration
1. Go to **Settings → Devices & Services → Unifi Access**
2. Click on the three-dot menu (⋮) on the integration card
3. Select **Delete**
4. Restart Home Assistant
5. If you installed via HACS you can also uninstall the repository from HACS afterwards

# Troubleshooting

## Invalid API Key 

You have likely created a Unifi Protect token and you need to create a Unifi Access token

Please create an issue if you have a feature request and pull requests are always welcome!

# Support my work
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/aniskadri)

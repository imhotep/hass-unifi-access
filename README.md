# Unifi Access Custom Integration for Home Assistant

## There is now a core integration for Unifi Access so which one should I use? Will this HACS one continue to be maintained?
This integration will continue to be maintained for the foreseable future. There are some slight differences with the core version listed below:
- The core version uses button entities instead of lock entities. It requires a template entity in order to use the `lock` entity. This one does not.
- The core version offers auto discovery. This one does not.
- The core version requires setting up actions for door locking rules. Ths one does not.

- This is a basic integration of [Unifi Access](https://ui.com/door-access) in [Home Assistant](https://homeassistant.io). 
- If you have Unifi Access set up with UID this will likely *NOT* work although some people have reported success using the free version of UID. 
- _Camera Feeds are currently not offered by the API and therefore **NOT** supported_.

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
    - Doorbell Pressed (binary_sensor). Requires **Unifi Access Reader Pro G1/G2** otherwise always **off**. Only appears when **Use polling** is not selected!
    - Door Lock (lock). You can unlock or open a door, but locking is unsupported and only logs a warning.
    - Event entities (`event`): Door Event and Doorbell Press. These are only created when `Use polling` is not selected.


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
    - Doorbell Pressed (binary_sensor). Requires **Unifi Access Reader Pro G1/G2** otherwise always **off**. Only appears when **Use polling** is not selected!
    - Door Lock (lock). You can unlock or open a door, but locking is unsupported and only logs a warning.
    - Event entities (`event`): Door Event and Doorbell Press. These are only created when `Use polling` is not selected.

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
- `actor` # the user tied to the event, when available
- `authentication` # authentication source reported by the controller
- `method` # opened method, when provided by the controller
- `type`
- `result` # examples: `ACCESS`, `BLOCKED`, `INCOMPLETE`

#### Warning regarding Door Events
Door events are using an undocumented API. Sadly, in September 2025, the Unifi Access API introduced some bugs that we have worked around but these events are still not 100% reliable depending on your hub. I recommend using the [Alarm Manager webhooks](https://github.com/imhotep/hass-unifi-access/issues/185#issuecomment-3895814140) if you need a more reliable way to automate based on door events.

### Evacuation/Lockdown
The evacuation (unlock all doors) and lockdown (lock all doors) switches apply to all doors and gates and **will sound the alarm** no matter which configuration you currently have in your terminal settings. The status will not update currently (known issue).

### Thumbnail 
A thumbnail of when the door is last accessed/locked/unlocked.

### Door lock rules (only applies to UAH)
The following entities will be created: `input_select`, `input_number` and 2 `sensor` entities (end time and current rule).
You are able to select one of the following rules via the `input_select`:
- **keep_lock**: door is locked indefinitely
- **keep_unlock**: door is unlocked indefinitely
- **custom**: door is unlocked for a given interval (use the input_number to define how long. Default is 10 minutes).
- **reset**: clear all lock rules
- **lock_early**: locks the door if it's currently on an unlock schedule.
- **lock_now**: locks the door if it's currently on an unlock schedule OR if it's unlocked temporarily via a locking rule.

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

# Wishlist
- door code via service

# Troubleshooting

## Invalid API Key 

You have likely created a Unifi Protect token and you need to create a Unifi Access token

Please create an issue if you have a feature request and pull requests are always welcome!

# Support my work
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/aniskadri)

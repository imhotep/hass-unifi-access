# Unifi Access Custom Integration for Home Assistant

- This is a basic integration of [Unifi Access](https://ui.com/door-access) in [Home Assistant](https://homeassistant.io). 
- If you have Unifi Access set up with UID this will likely *NOT* work although some people have reported success using the free version of UID. 
- _Camera Feeds are currently not offered by the API and therefore **NOT** supported_.

# Supported hardware
- Unifi Access Hub (UAH) :white_check_mark:
- Unifi Access Hub (UAH-DOOR) :white_check_mark:
- Unifi Access Intercom (UA-Intercom) :white_check_mark:
- Unifi Access Hub Enterprise (UAH-Ent) :white_check_mark:
- Unifi Gate Hub (UGT) :white_check_mark:
- Unifi Access Ultra (UA-Ultra) :white_check_mark:
- Unifi Access Door Mini (UA-Hub-Door-Mini) :white_check_mark:

# Getting Unifi Access API Token
- Log in to Unifi Access and Click on Security -> Advanced -> API Token
- Create a new token and pick all permissions (this is *IMPORTANT*). At the very least pick: Space, Device and System Log.

# Installation (HACS)
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
    - Door Lock (lock). This will not show up immediately under the device but it should show up after a while. You can unlock (but not lock) a door
    - Event entities: Access and Doorbell Press


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
    - Door Lock (lock). This will not show up immediately under the device but it should show up after a while. You can unlock (but not lock) a door
    - Event entities: Access and Doorbell Press

# Events
This integration currently supports two type of events

## Doorbell Press Event
An entity will get created for each door. Every time the doorbell is pressed there will be a `unifi_access_doorbell_start` event that will be received by this entity with some metadata. The same event will also be fired on the Home Assistant Event Bus. You can listen to it via the Developer Tools. When the doorbell is either answered or canceled there will be a `unifi_access_doorbell_stop` event.

### Event metadata
- door_name
- door_id
- type # `unifi_access_doorbell_start` or `unifi_access_doorbell_stop`

## Access
An entity will get created for each door. Every time a door is accessed (entry, exit, app, api) there will be a `unifi_access_entry` or `unifi_access_exit` event that will be received by this entity with some metadata. The same event will also be fired on the Home Assistant Event Bus. You can listen to it via the Developer Tools.

### Event metadata
- door_name
- door_id
- authentication # this is the method used to initiate the event ("REMOTE_THROUGH_UAH" , "NFC" , "MOBILE_TAP" , "PIN_CODE")
- actor # this is the name of the user that accessed the door. If set to N/A that means UNAUTHORIZED ACCESS!
- type # `unifi_access_entry` or `unifi_access_exit`

### Evacuation/Lockdown
The evacuation (unlock all doors) and lockdown (lock all doors) switches apply to all doors and gates and **will sound the alarm** no matter which configuration you currently have in your terminal settings. The status will not update currently (known issue).

### Door lock rules (only applies to UAH)
The following entities will be created: `input_select`, `input_number` and 2 `sensor` entities (end time and current rule).
You are able to select one of the following rules via the `input_select`:
- **keep_lock**: door is locked indefinitely
- **keep_unlock**: door is unlocked indefinitely
- **custom**: door is unlocked for a given interval (use the input_number to define how long. Default is 10 minutes).
- **reset**: clear all lock rules
- **lock_early**: locks the door if it's currently on an unlock schedule.

# Example automation

```
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
# API Limitations
The Unifi Access API does *NOT* support door locking at the moment. You probably already have it set to automatically lock after a small delay anyway.

# Wishlist
- door code via service

Please create an issue if you have a feature request and pull requests are always welcome!

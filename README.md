# Unifi Access Custom Integration for Home Assistant (ALPHA)

This is a basic integration of Unifi Access in [Home Assistant](https://homeassistant.io). If you have Unifi Access set up with UID this will *NOT* work

# Getting Unifi Access API Token
- Log in to Unifi Access and Click on Security -> Advanced -> API Token
- Create a new token and pick all permissions (this is *IMPORTANT*)

# Installation (HACS)
- Add this repository as a custom repository in HACS
- Restart Home Assistant
- Add new Integration -> Unifi Access
- Enter your Unifi Access controller IP or Hostname (default is `unifi` or `UDMPRO`). No need to enter port or scheme
- Enter your API Token that you generated in Unifi Access
- It should find all of your doors and add two entities for each one
    - Door Position Sensor (binary_sensor)
    - Door Lock (this will not show up immediately under the device but it should show up after a while)


# Installation (manual)
- Clone this repository
- Copy the `custom_components/unifi_access` to your `config/custom_components` folder in Home Assistant.
- Restart Home Assistant
- Add new Integration -> Unifi Access
- Enter your Unifi Access controller IP or Hostname (default is `unifi` or `UDMPRO`). No need to enter port
- Enter your API Token that you generated in Unifi Access
- It should find all of your doors and add two entities for each one
    - Door Position Sensor (binary_sensor)
    - Door Lock (this will not show up immediately under the device but it should show up after a while)

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

# Wish list 
This integration is pretty basic for now but I would like to add support for the following
- Using websockets instead of polling and subsequently supporting doorbell presses and faster updates (only available in Unifi Access 1.20.11 and later)

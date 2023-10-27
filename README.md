# Unifi Access Custom Integration for Home Assistant (ALPHA)

This is a basic integration of Unifi Access in [Home Assistant](https://homeassistant.io). If you have Unifi Access set up with UID this will *NOT* work

# Installation (HACS)
- Add this repository as a custom repository in HACS
- Restart Home Assistant
- Add new Integration -> Unifi Access (sorry no logos for now)
- Enter your Unifi Access controller IP or Hostname (default is `unifi` or `UDMPRO`). No need to enter port
- Enter your API Token that you generated in Unifi Access -> Security -> Advanced -> API Token
- It should find all of your doors and add two entities for each one
    - Door Position Sensor (binary_sensor)
    - Door Lock (this will take a while to show up under the device but it should show up after a while)


# Installation (manual)
- Clone this repository
- Copy the `custom_components/unifi_access` to your `config/custom_components` folder in Home Assistant.
- Restart Home Assistant
- Add new Integration -> Unifi Access (sorry no logos for now)
- Enter your Unifi Access controller IP or Hostname (default is `unifi` or `UDMPRO`). No need to enter port
- Enter your API Token that you generated in Unifi Access -> Security -> Advanced -> API Token
- It should find all of your doors and add two entities for each one
    - Door Position Sensor (binary_sensor)
    - Door Lock (this will take a while to show up under the device but it should show up after a while)

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

# Wish list 
This integration is pretty basic but I would like to add support for the following
- Using websockets instead of polling and subsequently supporting doorbell presses and faster updates (only available in Unifi Access 1.20.11 and later)

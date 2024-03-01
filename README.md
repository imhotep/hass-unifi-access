# Unifi Access Custom Integration for Home Assistant

This is a basic integration of Unifi Access in [Home Assistant](https://homeassistant.io). If you have Unifi Access set up with UID this will *NOT* work

# Getting Unifi Access API Token
- Log in to Unifi Access and Click on Security -> Advanced -> API Token
- Create a new token and pick all permissions (this is *IMPORTANT*)

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
- actor # this is the name of the user that accessed the door. If set to N/A that means UNAUTHORIZED ACCESS!
- type # `unifi_access_entry` or `unifi_access_exit`

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

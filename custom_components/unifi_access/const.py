"""Constants for the Unifi Access integration."""

DOMAIN = "unifi_access"

from unifi_access_api.const import (
    DEVICE_NOTIFICATIONS_URL,
    DOOR_LOCK_RULE_URL,
    DOOR_UNLOCK_URL,
    DOORS_EMERGENCY_URL,
    DOORS_URL,
    STATIC_URL,
    UNIFI_ACCESS_API_PORT,
)

DOORBELL_EVENT = "doorbell_press"
DOORBELL_START_EVENT = "unifi_access_doorbell_start"
DOORBELL_STOP_EVENT = "unifi_access_doorbell_stop"
ACCESS_EVENT = "unifi_access_{type}"
ACCESS_ENTRY_EVENT = "unifi_access_entry"
ACCESS_EXIT_EVENT = "unifi_access_exit"

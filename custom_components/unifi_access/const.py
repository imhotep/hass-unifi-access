"""Constants for the Unifi Access integration."""

DOMAIN = "unifi_access"

# URLs
UNIFI_ACCESS_API_PORT = 12445
DOORS_URL = "/api/v1/developer/doors"
DOOR_UNLOCK_URL = "/api/v1/developer/doors/{door_id}/unlock"
DOOR_LOCK_RULE_URL = "/api/v1/developer/doors/{door_id}/lock_rule"
DEVICE_NOTIFICATIONS_URL = "/api/v1/developer/devices/notifications"
DOORS_EMERGENCY_URL = "/api/v1/developer/doors/settings/emergency"
STATIC_URL = "/api/v1/developer/system/static"

DOORBELL_EVENT = "doorbell_press"
DOORBELL_START_EVENT = "unifi_access_doorbell_start"
DOORBELL_STOP_EVENT = "unifi_access_doorbell_stop"
ACCESS_EVENT = "unifi_access_{type}"
ACCESS_ENTRY_EVENT = "unifi_access_entry"
ACCESS_EXIT_EVENT = "unifi_access_exit"

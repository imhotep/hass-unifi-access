"""Constants for the Unifi Access integration."""

DOMAIN = "unifi_access"

# URLs
UNIFI_ACCESS_API_PORT = 12445
DOORS_URL = "/api/v1/developer/doors"
DOOR_LOCK_URL = "/api/v1/developer/doors/{door_id}/lock"
DOOR_UNLOCK_URL = "/api/v1/developer/doors/{door_id}/unlock"

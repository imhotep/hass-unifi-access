"""Constants for the Unifi Access integration."""

DOMAIN = "unifi_access"

# Door entity types — controls which HA platform entity a door appears as
DOOR_TYPE_LOCK = "lock"
DOOR_TYPE_GARAGE = "garage"
DOOR_TYPE_GATE = "gate"
DOOR_TYPES = [DOOR_TYPE_LOCK, DOOR_TYPE_GARAGE, DOOR_TYPE_GATE]

# Storage (for door type)
STORAGE_KEY = "unifi_access_entity_types"
STORAGE_VERSION = 1

# Doorbell event types
DOORBELL_EVENT = "doorbell_press"
DOORBELL_START_EVENT = "unifi_access_doorbell_start"
DOORBELL_STOP_EVENT = "unifi_access_doorbell_stop"

# Access event types
ACCESS_ENTRY_EVENT = "unifi_access_entry"
ACCESS_EXIT_EVENT = "unifi_access_exit"
ACCESS_GENERIC_EVENT = "unifi_access_access"

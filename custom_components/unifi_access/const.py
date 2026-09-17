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

# Storage (for per-door double-driveway mode, UGT/UA Hub Gate only)
DOUBLE_DRIVEWAY_STORAGE_KEY = "unifi_access_double_driveway_mode"
DOUBLE_DRIVEWAY_STORAGE_VERSION = 1

# Options flow key: list of door_ids the installer has declared as actually
# wired for double-driveway (dual-relay) operation. A UGT hub can service
# multiple doors (e.g. a driveway gate AND a pedestrian gate) that share the
# same hub device/type but are wired differently — the Access API has no
# field reporting which one is dual-relay, so this has to be declared once
# at config time rather than shown as a switch on every UGT door.
CONF_DOUBLE_DRIVEWAY_ELIGIBLE_DOORS = "double_driveway_eligible_doors"

# Hub device_type reported by the API for UA Hub Gate/Garage controllers.
# Access API reference 7.9: only UGT hubs accept entry_method=in/out
# (double-driveway mode) or control_cmd=open/close/stop (three-button mode).
# These are two independent query parameters on the same unlock endpoint,
# not two values of the same one -- control_cmd=in/out looks plausible from
# the reference table but silently fires only the entry relay either way;
# confirmed against a live double-driveway UA Hub Gate.
HUB_TYPE_UGT = "UGT"

# Gate motor directions, valid only for UGT doors with double-driveway
# mode enabled on the hub (Access API reference 7.9, entry_method=in/out).
GATE_DIRECTION_IN = "in"
GATE_DIRECTION_OUT = "out"

# Hub types that support the intercom guard ID feature (UA-Intercom directory)
INTERCOM_HUB_TYPES: frozenset[str] = frozenset({"UA-Intercom", "UA-G3-Intercom"})

# Doorbell event types
DOORBELL_EVENT = "doorbell_press"
DOORBELL_START_EVENT = "unifi_access_doorbell_start"
DOORBELL_STOP_EVENT = "unifi_access_doorbell_stop"

# Access event types
ACCESS_ENTRY_EVENT = "unifi_access_entry"
ACCESS_EXIT_EVENT = "unifi_access_exit"
ACCESS_GENERIC_EVENT = "unifi_access_access"

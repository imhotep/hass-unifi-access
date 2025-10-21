# Unicode Fix for German Umlaut Characters

## Problem
The UniFi Access integration failed to detect doorbell events when device names contained German umlauts (ö, ä, ü). This happened because Unicode characters can be represented in different forms (NFC vs NFD normalization).

## Solution
Added Unicode normalization to ensure consistent door name matching:

### Changes in `custom_components/unifi_access/hub.py`:

1. **Added normalization function** (line ~58):
```python
def normalize_door_name(name):
    """Normalize door name to handle Unicode characters consistently."""
    if not name or not isinstance(name, str):
        return name
    return unicodedata.normalize('NFC', name.strip())
```

2. **Updated door storage** (line ~259):
```python
# Normalize door name when storing
if "display_name" in door_data:
    door_data["display_name"] = normalize_door_name(door_data["display_name"])
```

3. **Fixed WebSocket matching** (line ~390):
```python
# Normalize door name from event for matching
event_door_name = normalize_door_name(device.get("display_name", ""))
```

## Testing
Verified with Docker Python 3.11 environment:
- ✅ Handles German umlauts correctly: "Türklingel", "Büro Tür", "Außentür"
- ✅ Maintains compatibility with ASCII door names
- ✅ Handles edge cases (empty strings, whitespace)

## Impact
German users can now reliably receive doorbell notifications when their UniFi Access devices have names containing ö, ä, ü characters.
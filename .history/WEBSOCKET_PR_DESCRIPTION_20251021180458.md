# Fix websocket-client Dependency Requirement

## Problem Description
Newer Home Assistant versions showed the error: "Setup failed for custom integration 'unifi_access': Requirements for unifi_access not found: ['websocket-client==1.8.0']."

**Root Cause:** The exact version pinning (`websocket-client==1.8.0`) in the manifest.json prevented Home Assistant from using compatible newer versions of websocket-client, causing installation failures when the specific version was not available or incompatible with the Home Assistant environment.

## Solution Implemented

### Changes Made in `custom_components/unifi_access/manifest.json`:

1. **Updated websocket-client dependency** (line 11):
   - **Before:** `"websocket-client==1.8.0"` (exact version)
   - **After:** `"websocket-client>=1.8.0"` (minimum version)
   - Allows Home Assistant to use compatible newer versions (current latest: 1.9.0)

2. **Version bump** (line 14):
   - Updated integration version from `1.3.2` to `1.3.3`

### Technical Details:
- Uses minimum version requirement instead of exact pinning
- Maintains compatibility with websocket-client 1.8.0 and newer
- Follows Home Assistant best practices for dependency management
- Prevents installation conflicts in newer HA environments

## Testing Performed

### Compatibility Verification:
- **Current stable version**: websocket-client 1.9.0 available
- **Backward compatibility**: Maintains support for 1.8.0 features used by integration
- **No breaking changes**: All existing websocket functionality preserved

### Integration Testing:
- Verified manifest.json syntax is valid
- Confirmed no additional dependencies are required
- Tested that websocket import and WebSocketApp functionality remain unchanged

## Impact
- **Installation reliability** improved for newer Home Assistant versions
- **Dependency flexibility** allows Home Assistant to choose compatible versions
- **No breaking changes** - existing installations continue to work unchanged  
- **Future-proof** dependency management prevents similar issues with version updates

## Files Modified
- `custom_components/unifi_access/manifest.json`: Updated websocket-client dependency requirement and version
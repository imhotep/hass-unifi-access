#!/usr/bin/env python3
"""
Test script to verify the Unicode normalization fix works correctly.
"""

import unicodedata

def normalize_door_name(name: str) -> str:
    """Normalize door name for comparison.
    
    This function normalizes Unicode strings to handle special characters
    like German umlauts (ö, ä, ü) correctly. It converts to NFC (canonical
    composition) normalization form and strips whitespace.
    """
    if not name:
        return ""
    return unicodedata.normalize('NFC', name.strip())

def test_unicode_fix():
    """Test the Unicode normalization fix."""
    print("=== Unicode Normalization Fix Test ===\n")
    
    # Test cases that would fail without normalization
    test_cases = [
        ("Haustür", "Haustu\u0308r"),  # ü in composed vs decomposed form
        ("Bürotür", "Bu\u0308rotu\u0308r"),  # Multiple ü decomposed
        ("Außentür", "Au\u00dfentu\u0308r"),  # ß + decomposed ü
    ]
    
    all_passed = True
    
    for i, (name1, name2) in enumerate(test_cases, 1):
        # Without normalization (old behavior - would fail)
        direct_match = name1 == name2
        
        # With normalization (new behavior - should work)
        normalized1 = normalize_door_name(name1)
        normalized2 = normalize_door_name(name2)
        normalized_match = normalized1 == normalized2
        
        print(f"Test {i}: '{name1}' vs '{name2}'")
        print(f"  Direct comparison: {direct_match}")
        print(f"  Normalized comparison: {normalized_match}")
        print(f"  Fix works: {'✓' if normalized_match else '✗'}")
        
        if not normalized_match:
            all_passed = False
        print()
    
    # Simulate doorbell matching
    print("=== Door Matching Simulation ===\n")
    
    # Doors as they would be stored (normalized)
    doors = {
        "door1": normalize_door_name("Haustür"),
        "door2": normalize_door_name("Bürotür"), 
        "door3": normalize_door_name("Außenbereich Tür"),
    }
    
    # WebSocket messages with potentially different encodings
    websocket_names = [
        "Haustür",                    # Normal
        "Haustu\u0308r",             # Decomposed ü
        "Bürotür",                   # Normal 
        "Bu\u0308rotu\u0308r",        # Decomposed ü
        "Außenbereich Tür",          # Normal
        "Au\u00dfenbereich Tu\u0308r", # Mixed encoding
        "Unknown Door"               # Should not match
    ]
    
    print("Stored doors:", list(doors.values()))
    print("\nTesting WebSocket door name matching:")
    
    for i, ws_name in enumerate(websocket_names, 1):
        normalized_ws_name = normalize_door_name(ws_name)
        
        # Find matching door (new logic)
        matched_door = None
        for door_id, door_name in doors.items():
            if normalize_door_name(door_name) == normalized_ws_name:
                matched_door = door_id
                break
        
        print(f"{i}. WebSocket: '{ws_name}'")
        print(f"   Normalized: '{normalized_ws_name}'")
        print(f"   Match: {matched_door if matched_door else 'None'}")
        
        if ws_name != "Unknown Door" and not matched_door:
            all_passed = False
        print()
    
    print("=== Result ===")
    if all_passed:
        print("✅ All tests PASSED! The Unicode fix works correctly.")
        print("   German umlauts in door names will now work with doorbell events.")
        return 0
    else:
        print("❌ Some tests FAILED! The fix needs more work.")
        return 1

if __name__ == "__main__":
    exit(test_unicode_fix())
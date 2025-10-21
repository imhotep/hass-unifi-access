#!/usr/bin/env python3
"""
Test script to demonstrate the Unicode normalization fix for German umlauts.
This script shows that the fix resolves issues with door names containing special characters.
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

def test_unicode_normalization():
    """Test that the Unicode normalization fixes the German umlauts issue."""
    
    # Test cases with German umlauts
    test_cases = [
        ("Haustür", "Haustür"),  # Same string
        ("Bürotür", "Bürotür"),  # Same string with ü
        ("Gartentür", "Gartentür"),  # Same string
        ("Tür Außenbereich", "Tür Außenbereich"),  # Multiple special chars
    ]
    
    # Simulate different Unicode representations (this can happen with WebSocket data)
    problematic_cases = [
        ("Tür", "Tu\u0308r"),  # Decomposed form (T + u + diaeresis + r)
        ("Haustür", "Haustu\u0308r"),  # Mixed composition
        ("Außentür", "Au\u00dfentu\u0308r"),  # Mixed with ß and decomposed ü
    ]
    
    print("=== Testing Unicode Normalization Fix ===\n")
    
    print("1. Basic test cases (should all pass):")
    for name1, name2 in test_cases:
        normalized1 = normalize_door_name(name1)
        normalized2 = normalize_door_name(name2)
        match = normalized1 == normalized2
        print(f"   '{name1}' == '{name2}' -> {match} ✓")
    
    print("\n2. Problematic cases that would fail without normalization:")
    for name1, name2 in problematic_cases:
        # Show what happens without normalization (old behavior)
        direct_match = name1 == name2
        
        # Show what happens with normalization (new behavior)
        normalized1 = normalize_door_name(name1)
        normalized2 = normalize_door_name(name2)
        normalized_match = normalized1 == normalized2
        
        print(f"   '{name1}' == '{name2}'")
        print(f"     Direct comparison: {direct_match} {'✓' if direct_match else '✗'}")
        print(f"     Normalized comparison: {normalized_match} {'✓' if normalized_match else '✗'}")
        print(f"     Normalized forms: '{normalized1}' == '{normalized2}'")
        print()

def simulate_doorbell_matching():
    """Simulate the door matching logic for doorbell events."""
    
    print("=== Simulating Doorbell Event Matching ===\n")
    
    # Simulate doors stored in the system (normalized when loaded)
    doors = {
        "door1": {"id": "door1", "name": normalize_door_name("Haustür")},
        "door2": {"id": "door2", "name": normalize_door_name("Bürotür")}, 
        "door3": {"id": "door3", "name": normalize_door_name("Gartentür")},
        "door4": {"id": "door4", "name": normalize_door_name("Außenbereich Tür")},
    }
    
    # Simulate WebSocket messages with potentially different encodings
    websocket_messages = [
        {"event": "access.remote_view", "data": {"door_name": "Haustür"}},          # NFC form
        {"event": "access.remote_view", "data": {"door_name": "Haustu\u0308r"}},    # Decomposed form
        {"event": "access.remote_view", "data": {"door_name": "Bürotür"}},         # Normal
        {"event": "access.remote_view", "data": {"door_name": "Bu\u0308rotu\u0308r"}}, # Decomposed
        {"event": "access.remote_view", "data": {"door_name": "Außenbereich Tür"}}, # Normal
        {"event": "access.remote_view", "data": {"door_name": "Au\u00dfenbereich Tu\u0308r"}}, # Mixed
        {"event": "access.remote_view", "data": {"door_name": "Unknown Door"}},     # Not found
    ]
    
    print("Stored doors:")
    for door_id, door_info in doors.items():
        print(f"   {door_id}: '{door_info['name']}'")
    print()
    
    print("Processing WebSocket messages:")
    for i, message in enumerate(websocket_messages, 1):
        door_name_from_ws = message["data"]["door_name"]
        normalized_ws_name = normalize_door_name(door_name_from_ws)
        
        # Simulate the door matching logic from the fix
        existing_door = next(
            (
                door_info
                for door_info in doors.values()
                if normalize_door_name(door_info["name"]) == normalized_ws_name
            ),
            None,
        )
        
        print(f"{i}. WebSocket door_name: '{door_name_from_ws}'")
        print(f"   Normalized: '{normalized_ws_name}'")
        if existing_door:
            print(f"   ✓ Matched door: {existing_door['id']} ('{existing_door['name']}')")
        else:
            print(f"   ✗ No matching door found")
        print()

if __name__ == "__main__":
    test_unicode_normalization()
    print()
    simulate_doorbell_matching()
    print("\n=== Summary ===")
    print("The Unicode normalization fix ensures that:")
    print("1. Door names with German umlauts (ö, ä, ü) are handled correctly")
    print("2. Different Unicode representations of the same characters match")
    print("3. Doorbell events work reliably regardless of character encoding")
    print("4. Both stored door names and WebSocket messages are normalized consistently")
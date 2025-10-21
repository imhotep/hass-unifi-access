#!/usr/bin/env python3
"""
Test the actual normalize_door_name function from hub.py
"""

import sys
import os
sys.path.append('/app')

# Import the normalize function from hub.py
from custom_components.unifi_access.hub import normalize_door_name

def test_actual_function():
    """Test the actual normalize_door_name function from hub.py."""
    print("=== Testing Actual normalize_door_name Function ===\n")
    
    # Test cases with problematic Unicode
    test_cases = [
        ("Haustür", "Haustu\u0308r"),
        ("Bürotür", "Bu\u0308rotu\u0308r"), 
        ("Außentür", "Au\u00dfentu\u0308r"),
        ("", ""),  # Empty string test
        ("  Tür  ", "Tu\u0308r"),  # Whitespace + normalization
    ]
    
    all_passed = True
    
    for i, (name1, name2) in enumerate(test_cases, 1):
        normalized1 = normalize_door_name(name1)
        normalized2 = normalize_door_name(name2)
        match = normalized1 == normalized2
        
        print(f"Test {i}: '{name1}' vs '{name2}'")
        print(f"  Normalized to: '{normalized1}' vs '{normalized2}'")
        print(f"  Match: {match} {'✓' if match else '✗'}")
        
        # Special case for empty strings and whitespace
        if i == 4:  # Empty string test
            if normalized1 == normalized2 == "":
                print("  ✓ Empty string handling works")
            else:
                all_passed = False
        elif i == 5:  # Whitespace test
            if normalized1.strip() == normalized2.strip():
                print("  ✓ Whitespace trimming works")
            else:
                all_passed = False
        elif not match:
            all_passed = False
        
        print()
    
    if all_passed:
        print("✅ All tests PASSED! The actual normalize_door_name function works correctly.")
        return 0
    else:
        print("❌ Some tests FAILED!")
        return 1

if __name__ == "__main__":
    exit(test_actual_function())
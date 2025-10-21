#!/usr/bin/env python3
"""
Test the normalize_door_name function in isolation
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

def test_normalize_function():
    """Test the normalize_door_name function."""
    print("=== Testing normalize_door_name Function ===\n")
    
    # Test edge cases and real scenarios
    test_cases = [
        # Basic functionality
        ("Haustür", "Haustu\u0308r", "Different Unicode forms should match"),
        ("Bürotür", "Bu\u0308rotu\u0308r", "Multiple decomposed characters"),
        ("Außentür", "Au\u00dfentu\u0308r", "Mixed composed and decomposed"),
        
        # Edge cases
        ("", "", "Empty strings"),
        ("  Tür  ", "Tu\u0308r", "Whitespace handling"),
        ("Normal Door", "Normal Door", "ASCII only names"),
        (" ", "", "Whitespace only"),
        
        # Real German door names
        ("Büroeingang", "Bu\u0308roeingang", "Office entrance"),
        ("Gartentür", "Gartentu\u0308r", "Garden door"),
        ("Küche", "Ku\u0308che", "Kitchen"),
    ]
    
    passed = 0
    failed = 0
    
    for i, (name1, name2, description) in enumerate(test_cases, 1):
        normalized1 = normalize_door_name(name1)
        normalized2 = normalize_door_name(name2)
        match = normalized1 == normalized2
        
        print(f"Test {i}: {description}")
        print(f"  Input 1: '{name1}' -> '{normalized1}'")
        print(f"  Input 2: '{name2}' -> '{normalized2}'")
        print(f"  Match: {match} {'✅' if match else '❌'}")
        
        if match:
            passed += 1
        else:
            failed += 1
        print()
    
    print("=== Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("🎉 All tests PASSED! The Unicode normalization fix is working correctly.")
        print("   German users can now use doorbell features with umlauts in device names!")
        return 0
    else:
        print("❌ Some tests failed. The fix needs adjustment.")
        return 1

if __name__ == "__main__":
    exit(test_normalize_function())
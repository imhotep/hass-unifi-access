#!/usr/bin/env python3
"""Basic test script to verify user management implementation."""

import sys
import os

# Add the custom_components path to sys.path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'unifi_access'))

def test_user_class():
    """Test that UnifiAccessUser class can be instantiated."""
    try:
        from user import UnifiAccessUser
        
        # Mock hub object with required methods
        class MockHub:
            def update_user_status(self, user_id, enabled):
                print(f"Mock: updating user {user_id} status to {'enabled' if enabled else 'disabled'}")
                
            def update_user_pin(self, user_id, pin):
                print(f"Mock: updating user {user_id} PIN")
        
        mock_hub = MockHub()
        
        # Create user instance with proper constructor arguments
        user = UnifiAccessUser(
            user_id="test-user-123",
            username="testuser",
            full_name="Test User",
            email="test@example.com", 
            status="active",
            pin_code="1234",
            hub=mock_hub
        )
        
        print(f"✓ UnifiAccessUser created successfully")
        print(f"  - ID: {user.id}")
        print(f"  - Name: {user.full_name}")
        print(f"  - Email: {user.email}")
        print(f"  - Status: {user.status}")
        print(f"  - Enabled: {user.is_enabled}")
        print(f"  - Has PIN: {user.has_pin}")
        
        # Test enable/disable methods
        print("✓ Testing enable/disable methods...")
        user.disable()
        user.enable()
        
        print("✓ User class test passed!")
        return True
        
    except Exception as e:
        print(f"✗ User class test failed: {e}")
        return False

def test_constants():
    """Test that constants are properly defined."""
    try:
        from const import USERS_URL, USER_UPDATE_URL
        
        expected_users_url = "/api/v1/developer/users"
        expected_update_url = "/api/v1/developer/users/{user_id}"
        
        assert USERS_URL == expected_users_url, f"Expected {expected_users_url}, got {USERS_URL}"
        assert USER_UPDATE_URL == expected_update_url, f"Expected {expected_update_url}, got {USER_UPDATE_URL}"
        
        print("✓ Constants test passed!")
        print(f"  - USERS_URL: {USERS_URL}")
        print(f"  - USER_UPDATE_URL: {USER_UPDATE_URL}")
        return True
        
    except Exception as e:
        print(f"✗ Constants test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running basic functionality tests for UniFi Access user management...\n")
    
    results = []
    results.append(test_constants())
    results.append(test_user_class())
    
    print(f"\nTest Summary:")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All tests passed! The user management implementation looks good.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
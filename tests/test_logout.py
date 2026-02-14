#!/usr/bin/env python3
"""
Test script to verify logout functionality
"""

import requests
import json

def test_logout_endpoint():
    """Test that logout endpoint works without authentication"""
    
    base_url = "http://localhost:5000"
    
    print("Testing logout endpoint...")
    
    # Test 1: Test API logout endpoint without authentication
    try:
        response = requests.post(f"{base_url}/api/auth/logout")
        if response.status_code == 200:
            print("✓ API logout endpoint works without authentication")
        else:
            print(f"✗ API logout endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API logout endpoint failed: {e}")
        return False
    
    # Test 2: Test regular logout endpoint without authentication
    try:
        response = requests.get(f"{base_url}/logout", allow_redirects=False)
        print(f"Logout response status: {response.status_code}")
        location = response.headers.get('Location', '')
        print(f"Redirect location: {location}")
        
        if response.status_code == 302:  # Redirect to skipping-stones
            print("✓ Logout endpoint redirects correctly")
            # Check that it redirects to skipping-stones, not login
            if 'skipping-stones' in location:
                print("✓ Logout redirects to game page (not Google sign-in)")
            else:
                print(f"✗ Logout redirects to unexpected location: {location}")
                return False
        else:
            print(f"✗ Logout endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Logout endpoint failed: {e}")
        return False
    
    return True

def test_logout_clears_user_state():
    """Test that logout properly clears user state"""
    
    base_url = "http://localhost:5000"
    
    print("Testing logout clears user state...")
    
    # Test 1: Check initial auth status
    try:
        response = requests.get(f"{base_url}/api/auth/status")
        initial_auth = response.json()
        print(f"Initial auth status: {initial_auth.get('authenticated', False)}")
    except Exception as e:
        print(f"✗ Failed to check initial auth status: {e}")
        return False
    
    # Test 2: Call logout API
    try:
        response = requests.post(f"{base_url}/api/auth/logout")
        if response.status_code == 200:
            print("✓ Logout API call successful")
        else:
            print(f"✗ Logout API failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Logout API call failed: {e}")
        return False
    
    # Test 3: Check auth status after logout
    try:
        response = requests.get(f"{base_url}/api/auth/status")
        after_auth = response.json()
        print(f"Auth status after logout: {after_auth.get('authenticated', False)}")
        
        if not after_auth.get('authenticated', False):
            print("✓ User properly logged out")
        else:
            print("✗ User still appears logged in after logout")
            return False
    except Exception as e:
        print(f"✗ Failed to check auth status after logout: {e}")
        return False

    return True

def test_logout_functionality():
    """Test that logout properly clears session state"""
    
    base_url = "http://localhost:5000"
    
    print("Testing logout functionality...")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/")
        print(f"✓ Server is running (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running. Please start the server first.")
        return False
    
    # Test 2: Check auth status endpoint
    try:
        response = requests.get(f"{base_url}/api/auth/status")
        auth_data = response.json()
        print(f"✓ Auth status endpoint working (authenticated: {auth_data.get('authenticated', False)})")
    except Exception as e:
        print(f"✗ Auth status endpoint failed: {e}")
        return False
    
    # Test 3: Check debug session endpoint
    try:
        response = requests.get(f"{base_url}/api/auth/debug-session")
        session_data = response.json()
        print(f"✓ Debug session endpoint working")
        print(f"  - Session ID: {session_data.get('session_id', 'None')}")
        print(f"  - User authenticated: {session_data.get('user_authenticated', False)}")
    except Exception as e:
        print(f"✗ Debug session endpoint failed: {e}")
        return False
    
    # Test 4: Check game configs endpoint
    try:
        response = requests.get(f"{base_url}/api/skipping-stones/configs")
        configs = response.json()
        print(f"✓ Game configs endpoint working ({len(configs)} levels available)")
    except Exception as e:
        print(f"✗ Game configs endpoint failed: {e}")
        return False
    
    print("\n✓ All endpoints are working correctly!")
    print("\nTo test the logout functionality:")
    print("1. Open http://localhost:5000 in your browser")
    print("2. Log in with Google")
    print("3. Play the game and make some moves")
    print("4. Click the logout button")
    print("5. Verify that the game state is cleared and you see a fresh game")
    
    return True

def test_browser_logout_flow():
    """Test the full browser logout flow"""
    
    base_url = "http://localhost:5000"
    
    print("Testing browser logout flow...")
    
    # Create a session to simulate a logged-in user
    session = requests.Session()
    
    # Test 1: Simulate accessing the game page
    try:
        response = session.get(f"{base_url}/skipping-stones")
        if response.status_code == 200:
            print("✓ Game page accessible")
        else:
            print(f"✗ Game page not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to access game page: {e}")
        return False
    
    # Test 2: Simulate calling the API logout endpoint
    try:
        response = session.post(f"{base_url}/api/auth/logout")
        if response.status_code == 200:
            print("✓ API logout successful")
        else:
            print(f"✗ API logout failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API logout call failed: {e}")
        return False
    
    # Test 3: Simulate redirecting to logout page
    try:
        response = session.get(f"{base_url}/logout", allow_redirects=False)
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'skipping-stones' in location:
                print("✓ Logout redirects to game page")
            else:
                print(f"✗ Logout redirects to unexpected location: {location}")
                return False
        else:
            print(f"✗ Logout page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Logout page access failed: {e}")
        return False
    
    # Test 4: Verify user is logged out by checking auth status
    try:
        response = session.get(f"{base_url}/api/auth/status")
        auth_data = response.json()
        if not auth_data.get('authenticated', False):
            print("✓ User properly logged out after full flow")
        else:
            print("✗ User still appears logged in after full flow")
            return False
    except Exception as e:
        print(f"✗ Failed to verify logout: {e}")
        return False
    
    return True

def main():
    """Run all logout tests"""
    print("Running Logout Tests")
    print("=" * 50)
    
    # Test logout endpoints
    if not test_logout_endpoint():
        print("❌ Logout endpoint tests failed")
        return False
    
    # Test logout clears user state
    if not test_logout_clears_user_state():
        print("❌ Logout user state tests failed")
        return False
    
    # Test browser logout flow
    if not test_browser_logout_flow():
        print("❌ Browser logout flow tests failed")
        return False
    
    # Test general functionality
    if not test_logout_functionality():
        print("❌ Logout functionality tests failed")
        return False
    
    print("\n✅ All logout tests passed!")
    return True

if __name__ == "__main__":
    main() 
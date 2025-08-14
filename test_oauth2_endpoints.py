#!/usr/bin/env python3
"""
Test OAuth2 token endpoints to see what credentials are required
"""

import requests
import json
import time
from urllib.parse import urlencode

def test_oauth2_endpoints():
    """Test various OAuth2 endpoints to understand requirements"""
    print("🔍 Testing OAuth2 Token Endpoints")
    print("=" * 50)
    
    # Test 1: Check authorization endpoint
    print("\n📋 TEST 1: AUTHORIZATION ENDPOINT")
    print("-" * 30)
    auth_url = "https://digitalturbine.okta.com/oauth2/v1/authorize"
    auth_params = {
        "client_id": "0oa9je4h93zNQwyuf697",
        "response_type": "code",
        "redirect_uri": "https://savanna.fyber.com/oauth/okta/callback",
        "scope": "openid profile groups",
        "state": "test_state_123",
        "nonce": "test_nonce_456"
    }
    
    full_auth_url = f"{auth_url}?{urlencode(auth_params)}"
    print(f"Authorization URL: {full_auth_url}")
    
    try:
        response = requests.get(full_auth_url, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Authorization endpoint accessible")
        else:
            print(f"⚠️ Authorization endpoint returned: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error accessing authorization endpoint: {e}")
    
    # Test 2: Check token endpoint (without credentials)
    print("\n🔑 TEST 2: TOKEN ENDPOINT (NO CREDENTIALS)")
    print("-" * 40)
    token_url = "https://digitalturbine.okta.com/oauth2/v1/token"
    
    # Test with minimal data
    test_data = {
        "grant_type": "authorization_code",
        "code": "test_code_123",
        "redirect_uri": "https://savanna.fyber.com/oauth/okta/callback",
        "client_id": "0oa9je4h93zNQwyuf697"
    }
    
    try:
        response = requests.post(token_url, data=test_data, timeout=15)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 400:
            print("✅ Token endpoint accessible (expected 400 for invalid code)")
        elif response.status_code == 401:
            print("🔐 Token endpoint requires authentication")
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing token endpoint: {e}")
    
    # Test 3: Check if client secret is required
    print("\n🔐 TEST 3: CLIENT SECRET REQUIREMENT")
    print("-" * 35)
    
    # Test with fake client secret
    test_data_with_secret = {
        "grant_type": "authorization_code",
        "code": "test_code_123",
        "redirect_uri": "https://savanna.fyber.com/oauth/okta/callback",
        "client_id": "0oa9je4h93zNQwyuf697",
        "client_secret": "fake_secret_123"
    }
    
    try:
        response = requests.post(token_url, data=test_data_with_secret, timeout=15)
        print(f"Status with fake secret: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 400:
            print("✅ Client secret not required or fake secret accepted")
        elif response.status_code == 401:
            print("🔐 Client secret required and validated")
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing with client secret: {e}")
    
    # Test 4: Check refresh token endpoint
    print("\n🔄 TEST 4: REFRESH TOKEN ENDPOINT")
    print("-" * 35)
    
    # Test refresh token flow
    refresh_data = {
        "grant_type": "refresh_token",
        "refresh_token": "fake_refresh_token_123",
        "client_id": "0oa9je4h93zNQwyuf697"
    }
    
    try:
        response = requests.post(token_url, data=refresh_data, timeout=15)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 400:
            print("✅ Refresh token endpoint accessible (expected 400 for invalid token)")
        elif response.status_code == 401:
            print("🔐 Refresh token endpoint requires authentication")
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing refresh token endpoint: {e}")
    
    # Test 5: Check what error messages tell us
    print("\n📝 TEST 5: ERROR MESSAGE ANALYSIS")
    print("-" * 35)
    
    # Test with completely invalid data
    invalid_data = {
        "grant_type": "invalid_grant",
        "client_id": "invalid_client"
    }
    
    try:
        response = requests.post(token_url, data=invalid_data, timeout=15)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 400:
            try:
                error_data = response.json()
                error_type = error_data.get('error', 'unknown')
                error_description = error_data.get('error_description', 'no description')
                print(f"Error Type: {error_type}")
                print(f"Error Description: {error_description}")
                
                if 'client_secret' in error_description.lower():
                    print("🔐 Client secret is required")
                elif 'redirect_uri' in error_description.lower():
                    print("🌐 Redirect URI validation is strict")
                elif 'client_id' in error_description.lower():
                    print("🆔 Client ID validation failed")
                else:
                    print("ℹ️ Other validation error")
                    
            except:
                print(f"Raw error response: {response.text[:200]}...")
        else:
            print(f"Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing invalid data: {e}")
    
    print("\n✨ OAuth2 Endpoint Testing Complete!")
    print("\n📋 SUMMARY:")
    print("- Check the responses above to understand requirements")
    print("- Look for client_secret requirements")
    print("- Check if redirect_uri validation is strict")
    print("- Verify if refresh tokens are supported")

if __name__ == "__main__":
    test_oauth2_endpoints()


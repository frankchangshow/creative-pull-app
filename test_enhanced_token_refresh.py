#!/usr/bin/env python3
"""
Test script for the enhanced token refresh functionality
"""

from savanna_bearer_client import SavannaBearerClient
import json
import time
from datetime import datetime, timedelta

def test_enhanced_token_refresh():
    """Test all the new token refresh features"""
    print("🚀 Testing Enhanced Token Refresh Functionality")
    print("=" * 60)
    
    # Initialize the enhanced client
    client = SavannaBearerClient()
    
    # Test 1: Get detailed token information
    print("\n📋 TEST 1: TOKEN INFORMATION")
    print("-" * 40)
    token_info = client.get_token_info()
    print(json.dumps(token_info, indent=2, default=str))
    
    # Test 2: Test authentication endpoints
    print("\n🔐 TEST 2: AUTHENTICATION ENDPOINTS")
    print("-" * 40)
    client.test_authentication_endpoints()
    
    # Test 3: Test token refresh strategies
    print("\n🔄 TEST 3: TOKEN REFRESH STRATEGIES")
    print("-" * 40)
    print("Testing if token needs refresh...")
    needs_refresh = client.refresh_token_if_needed()
    print(f"Token refresh needed: {needs_refresh}")
    
    # Test 4: Smart posting with automatic token management
    print("\n📤 TEST 4: SMART POSTING")
    print("-" * 40)
    test_data = {
        "creative_id": f"test_enhanced_{int(time.time())}",
        "ad_network_id": 456,
        "creation_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "expire_date": (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S'),
        "active": True
    }
    
    print(f"Test data: {json.dumps(test_data, indent=2)}")
    result = client.smart_post_to_creative_pulling(test_data)
    
    if result:
        print("✅ Smart posting successful!")
        print(f"Result: {result}")
    else:
        print("❌ Smart posting failed")
    
    print("\n✨ Enhanced Token Refresh Test Complete!")

if __name__ == "__main__":
    test_enhanced_token_refresh()


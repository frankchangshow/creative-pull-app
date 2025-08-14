#!/usr/bin/env python3
"""
Aggressive Token Extraction System
Tries multiple methods to extract tokens from existing sessions
"""

import requests
import json
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, Any
import logging
import re
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AggressiveTokenExtractor:
    """Aggressive token extraction using multiple methods"""
    
    def __init__(self):
        self.session = requests.Session()
        self.savanna_base_url = "https://savanna.fyber.com"
        
        # Set realistic browser headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def extract_token_aggressive(self) -> Optional[str]:
        """Try multiple aggressive methods to extract token"""
        try:
            logger.info("🔥 Starting aggressive token extraction...")
            
            # Method 1: Direct page access with various headers
            token = self._try_direct_access()
            if token:
                return token
            
            # Method 2: Try different endpoints
            token = self._try_multiple_endpoints()
            if token:
                return token
            
            # Method 3: Simulate browser navigation
            token = self._simulate_browser_navigation()
            if token:
                return token
            
            # Method 4: Check for existing browser session
            token = self._check_browser_session()
            if token:
                return token
            
            logger.warning("⚠️ All aggressive methods failed")
            return None
            
        except Exception as e:
            logger.error(f"❌ Aggressive extraction failed: {e}")
            return None
    
    def _try_direct_access(self) -> Optional[str]:
        """Try direct access with various approaches"""
        try:
            logger.info("🎯 Method 1: Direct page access...")
            
            # Try 1: Basic GET request
            response = self.session.get(
                f"{self.savanna_base_url}/creative-pulling",
                timeout=10,
                allow_redirects=True
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response URL: {response.url}")
            
            if response.status_code == 200:
                # Extract token from response
                token = self._extract_token_from_response(response)
                if token:
                    logger.info("✅ Token found via direct access!")
                    return token
            
            # Try 2: With referer header
            self.session.headers.update({'Referer': 'https://savanna.fyber.com/'})
            response = self.session.get(
                f"{self.savanna_base_url}/creative-pulling",
                timeout=10,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                token = self._extract_token_from_response(response)
                if token:
                    return token
            
            # Try 3: Access main page first
            main_response = self.session.get(
                f"{self.savanna_base_url}/",
                timeout=10,
                allow_redirects=True
            )
            
            if main_response.status_code == 200:
                # Now try creative-pulling
                response = self.session.get(
                    f"{self.savanna_base_url}/creative-pulling",
                    timeout=10,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    token = self._extract_token_from_response(response)
                    if token:
                        return token
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Direct access failed: {e}")
            return None
    
    def _try_multiple_endpoints(self) -> Optional[str]:
        """Try multiple endpoints to find tokens"""
        try:
            logger.info("🔍 Method 2: Trying multiple endpoints...")
            
            endpoints_to_try = [
                "/creative-pulling",
                "/",
                "/dashboard",
                "/home",
                "/api/creative-pulling",
                "/api/creatives",
                "/oauth/okta/callback",
                "/authentication"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    logger.info(f"   Trying: {endpoint}")
                    response = self.session.get(
                        f"{self.savanna_base_url}{endpoint}",
                        timeout=10,
                        allow_redirects=True
                    )
                    
                    logger.info(f"      Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        # Extract token from response
                        token = self._extract_token_from_response(response)
                        if token:
                            logger.info(f"✅ Token found via endpoint: {endpoint}")
                            return token
                        
                        # Check cookies
                        token = self._extract_token_from_cookies()
                        if token:
                            logger.info(f"✅ Token found in cookies via endpoint: {endpoint}")
                            return token
                    
                    # Small delay between requests
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"      Error with {endpoint}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Multiple endpoints failed: {e}")
            return None
    
    def _simulate_browser_navigation(self) -> Optional[str]:
        """Simulate browser navigation flow"""
        try:
            logger.info("🌐 Method 3: Simulating browser navigation...")
            
            # Step 1: Access main page
            logger.info("   Step 1: Accessing main page...")
            main_response = self.session.get(
                f"{self.savanna_base_url}/",
                timeout=10,
                allow_redirects=True
            )
            
            logger.info(f"   Main page status: {main_response.status_code}")
            
            # Step 2: Check if we got redirected to login
            if "login" in main_response.url.lower() or "okta" in main_response.url.lower():
                logger.info("   Redirected to login page, checking for tokens...")
                token = self._extract_token_from_response(main_response)
                if token:
                    return token
            
            # Step 3: Try to access a protected resource
            logger.info("   Step 2: Trying protected resource...")
            protected_response = self.session.get(
                f"{self.savanna_base_url}/creative-pulling",
                timeout=10,
                allow_redirects=True
            )
            
            logger.info(f"   Protected resource status: {protected_response.status_code}")
            
            if protected_response.status_code == 200:
                token = self._extract_token_from_response(protected_response)
                if token:
                    return token
            
            # Step 4: Check if we got a different response
            if protected_response.status_code != 200:
                logger.info(f"   Got status {protected_response.status_code}, checking response...")
                token = self._extract_token_from_response(protected_response)
                if token:
                    return token
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Browser navigation simulation failed: {e}")
            return None
    
    def _check_browser_session(self) -> Optional[str]:
        """Check if there's an existing browser session we can access"""
        try:
            logger.info("🍪 Method 4: Checking browser session...")
            
            # Try to access with session cookies
            logger.info("   Checking session cookies...")
            
            # List all cookies we have
            cookies = self.session.cookies
            logger.info(f"   Found {len(cookies)} cookies:")
            for cookie in cookies:
                logger.info(f"      {cookie.name}: {cookie.value[:50]}...")
            
            # Try to access with existing cookies
            response = self.session.get(
                f"{self.savanna_base_url}/creative-pulling",
                timeout=10,
                allow_redirects=True
            )
            
            logger.info(f"   Session check status: {response.status_code}")
            
            if response.status_code == 200:
                token = self._extract_token_from_response(response)
                if token:
                    return token
            
            # Try authentication endpoint
            auth_response = self.session.get(
                f"{self.savanna_base_url}/authentication",
                timeout=10
            )
            
            logger.info(f"   Auth endpoint status: {auth_response.status_code}")
            
            if auth_response.status_code == 200:
                token = self._extract_token_from_response(auth_response)
                if token:
                    return token
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Browser session check failed: {e}")
            return None
    
    def _extract_token_from_response(self, response) -> Optional[str]:
        """Extract token from HTTP response"""
        try:
            # Look for token in response text
            text = response.text
            
            # Pattern 1: JWT token in script tags
            jwt_pattern = r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'
            jwt_matches = re.findall(jwt_pattern, text)
            
            for match in jwt_matches:
                if len(match) > 100:  # Likely a real JWT
                    logger.info(f"🔍 Found JWT token in response: {match[:20]}...")
                    return match
            
            # Pattern 2: Token in localStorage or similar
            token_patterns = [
                r'"accessToken"\s*:\s*"([^"]+)"',
                r'"token"\s*:\s*"([^"]+)"',
                r'"bearer"\s*:\s*"([^"]+)"',
                r'Bearer\s+([A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*)',
                r'localStorage\.setItem\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)',
                r'sessionStorage\.setItem\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)'
            ]
            
            for pattern in token_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if isinstance(match, tuple):
                        # Handle localStorage/sessionStorage patterns
                        for item in match:
                            if item.startswith('eyJ') and len(item) > 100:
                                logger.info(f"🔍 Found token in storage: {item[:20]}...")
                                return item
                    elif match.startswith('eyJ') and len(match) > 100:
                        logger.info(f"🔍 Found token with pattern: {match[:20]}...")
                        return match
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting token from response: {e}")
            return None
    
    def _extract_token_from_cookies(self) -> Optional[str]:
        """Extract token from cookies"""
        try:
            cookies = self.session.cookies
            
            # Look for common token cookie names
            token_cookies = [
                'feathers-jwt',
                'access_token',
                'jwt_token',
                'auth_token',
                'savanna_token',
                'okta_token',
                'bearer_token'
            ]
            
            for cookie_name in token_cookies:
                if cookie_name in cookies:
                    cookie_value = cookies[cookie_name]
                    if cookie_value.startswith('eyJ') and len(cookie_value) > 100:
                        logger.info(f"🔍 Found token in cookie {cookie_name}: {cookie_value[:20]}...")
                        return cookie_value
            
            # Check all cookies for JWT patterns
            for cookie in cookies:
                cookie_value = cookie.value
                if cookie_value.startswith('eyJ') and len(cookie_value) > 100:
                    logger.info(f"🔍 Found JWT in cookie {cookie.name}: {cookie_value[:20]}...")
                    return cookie_value
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting token from cookies: {e}")
            return None
    
    def test_aggressive_extraction(self):
        """Test the aggressive token extraction system"""
        print("🔥 Testing Aggressive Token Extraction")
        print("=" * 40)
        
        token = self.extract_token_aggressive()
        
        if token:
            print(f"\n🎉 SUCCESS! Extracted token: {token[:50]}...")
            
            # Validate the token
            if self._validate_token(token):
                print("✅ Token is valid and working!")
                return token
            else:
                print("⚠️ Token extracted but validation failed")
                return None
        else:
            print("\n❌ All extraction methods failed")
            return None
    
    def _validate_token(self, token: str) -> bool:
        """Validate extracted token by testing it"""
        try:
            logger.info("🔍 Validating extracted token...")
            
            # Test token with a simple API call
            test_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.savanna_base_url}/creative-pulling",
                headers=test_headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ Token validation successful!")
                return True
            elif response.status_code == 401:
                logger.warning("⚠️ Token validation failed - unauthorized")
                return False
            else:
                logger.warning(f"⚠️ Token validation returned status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error validating token: {e}")
            return False

def main():
    """Main test function"""
    print("🚀 Aggressive Token Extraction Test")
    print("=" * 40)
    
    extractor = AggressiveTokenExtractor()
    token = extractor.test_aggressive_extraction()
    
    if token:
        print(f"\n🎉 SUCCESS! Token extracted and validated!")
        print(f"Token: {token[:50]}...")
    else:
        print("\n❌ Token extraction failed")
        print("\n💡 Next steps:")
        print("1. Make sure you're logged into Savanna in your browser")
        print("2. Try refreshing the Savanna page")
        print("3. Check if you have any browser extensions blocking cookies")
    
    print("\n✨ Test complete!")

if __name__ == "__main__":
    main()


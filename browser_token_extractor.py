#!/usr/bin/env python3
"""
Browser-Based Token Extraction System
Extracts fresh tokens from active browser sessions without requiring OAuth2 credentials
"""

import requests
import json
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserTokenExtractor:
    """Extract tokens from browser sessions"""
    
    def __init__(self):
        self.session = requests.Session()
        self.savanna_base_url = "https://savanna.fyber.com"
        self.okta_base_url = "https://digitalturbine.okta.com"
        
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
    
    def extract_token_from_browser(self) -> Optional[str]:
        """Main method to extract token from browser"""
        try:
            logger.info("🌐 Starting browser-based token extraction...")
            
            # Step 1: Check if user has active session
            active_token = self._check_active_session()
            if active_token:
                logger.info("✅ Found active session token!")
                return active_token
            
            # Step 2: Open browser for login
            logger.info("🌐 No active session, opening browser for login...")
            if not self._open_browser_for_login():
                return None
            
            # Step 3: Wait for user to complete login
            logger.info("⏳ Waiting for user to complete login...")
            token = self._wait_for_user_login()
            
            if token:
                logger.info("✅ Successfully extracted token from browser!")
                return token
            else:
                logger.warning("⚠️ Could not extract token from browser")
                return None
                
        except Exception as e:
            logger.error(f"❌ Browser token extraction failed: {e}")
            return None
    
    def _check_active_session(self) -> Optional[str]:
        """Check if user already has an active Savanna session"""
        try:
            logger.info("🔍 Checking for active Savanna session...")
            
            # Try to access a protected page
            response = self.session.get(
                f"{self.savanna_base_url}/creative-pulling",
                timeout=10,
                allow_redirects=False
            )
            
            if response.status_code == 200:
                logger.info("✅ Active session found!")
                # Extract token from response or cookies
                token = self._extract_token_from_response(response)
                if token:
                    return token
            
            # Check cookies for tokens
            token = self._extract_token_from_cookies()
            if token:
                return token
            
            logger.info("ℹ️ No active session found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error checking active session: {e}")
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
                r'Bearer\s+([A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*)'
            ]
            
            for pattern in token_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if match.startswith('eyJ') and len(match) > 100:
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
                'savanna_token'
            ]
            
            for cookie_name in token_cookies:
                if cookie_name in cookies:
                    cookie_value = cookies[cookie_name]
                    if cookie_value.startswith('eyJ') and len(cookie_value) > 100:
                        logger.info(f"🔍 Found token in cookie {cookie_name}: {cookie_value[:20]}...")
                        return cookie_value
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting token from cookies: {e}")
            return None
    
    def _open_browser_for_login(self) -> bool:
        """Open browser to Savanna login page"""
        try:
            # Build login URL
            login_url = f"{self.savanna_base_url}/oauth/okta/authenticate"
            
            logger.info(f"🌐 Opening browser to: {login_url}")
            
            # Open browser
            webbrowser.open(login_url)
            
            # Show instructions to user
            self._show_login_instructions()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error opening browser: {e}")
            return False
    
    def _show_login_instructions(self):
        """Show login instructions to user"""
        try:
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            messagebox.showinfo(
                "🌐 Browser Login Required",
                "I've opened your browser to the Savanna login page.\n\n"
                "Please:\n"
                "1. Complete the Okta login in your browser\n"
                "2. Navigate to Savanna\n"
                "3. Come back to this app and click OK\n\n"
                "The app will then try to extract your fresh token!"
            )
            
            root.destroy()
            
        except Exception as e:
            logger.warning(f"⚠️ Could not show GUI instructions: {e}")
            print("\n🌐 BROWSER LOGIN INSTRUCTIONS:")
            print("1. Complete Okta login in your browser")
            print("2. Navigate to Savanna")
            print("3. Come back here and press Enter...")
            input("Press Enter when you've completed login...")
    
    def _wait_for_user_login(self) -> Optional[str]:
        """Wait for user to complete login and extract token"""
        try:
            logger.info("⏳ Waiting for user to complete login...")
            
            # Give user time to complete login
            time.sleep(2)
            
            # Try multiple times to extract token
            for attempt in range(5):
                logger.info(f"🔄 Attempt {attempt + 1}/5: Checking for fresh token...")
                
                # Try to access protected page
                response = self.session.get(
                    f"{self.savanna_base_url}/creative-pulling",
                    timeout=10,
                    allow_redirects=False
                )
                
                if response.status_code == 200:
                    # Extract token from response
                    token = self._extract_token_from_response(response)
                    if token:
                        return token
                
                # Check cookies
                token = self._extract_token_from_cookies()
                if token:
                    return token
                
                # Wait before next attempt
                if attempt < 4:
                    logger.info("⏳ Waiting 3 seconds before next attempt...")
                    time.sleep(3)
            
            logger.warning("⚠️ Could not extract token after multiple attempts")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error waiting for user login: {e}")
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
    
    def test_token_extraction(self):
        """Test the token extraction system"""
        print("🧪 Testing Browser Token Extraction")
        print("=" * 40)
        
        # Test 1: Check active session
        print("\n📋 TEST 1: CHECK ACTIVE SESSION")
        print("-" * 30)
        active_token = self._check_active_session()
        if active_token:
            print(f"✅ Active token found: {active_token[:20]}...")
        else:
            print("ℹ️ No active session found")
        
        # Test 2: Extract token from browser
        print("\n🌐 TEST 2: EXTRACT FROM BROWSER")
        print("-" * 30)
        print("This will open your browser to Savanna login...")
        
        token = self.extract_token_from_browser()
        if token:
            print(f"✅ Token extracted successfully: {token[:20]}...")
            
            # Validate token
            if self._validate_token(token):
                print("✅ Token is valid!")
                return token
            else:
                print("⚠️ Token appears to be invalid")
                return None
        else:
            print("❌ Failed to extract token")
            return None

def main():
    """Main test function"""
    print("🚀 Browser Token Extraction Test")
    print("=" * 40)
    
    extractor = BrowserTokenExtractor()
    token = extractor.test_token_extraction()
    
    if token:
        print(f"\n🎉 SUCCESS! Extracted token: {token[:50]}...")
    else:
        print("\n❌ Token extraction failed")
    
    print("\n✨ Test complete!")

if __name__ == "__main__":
    main()

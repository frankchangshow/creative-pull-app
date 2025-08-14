#!/usr/bin/env python3
"""
Enhanced Browser Token Extraction System
Follows the actual OAuth2 flow from HAR file analysis
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
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedTokenExtractor:
    """Enhanced token extraction following actual OAuth2 flow"""
    
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
    
    def extract_token_enhanced(self) -> Optional[str]:
        """Enhanced token extraction following OAuth2 flow"""
        try:
            logger.info("🚀 Starting enhanced token extraction...")
            
            # Step 1: Check if user has active session
            active_token = self._check_active_session()
            if active_token:
                logger.info("✅ Found active session token!")
                return active_token
            
            # Step 2: Follow the OAuth2 flow from HAR file
            logger.info("🔄 Following OAuth2 flow from HAR analysis...")
            
            # Step 2a: Start OAuth2 authorization
            auth_code = self._get_authorization_code()
            if not auth_code:
                logger.warning("⚠️ Could not get authorization code")
                return None
            
            # Step 2b: Exchange code for token
            token = self._exchange_code_for_token(auth_code)
            if token:
                logger.info("✅ Successfully obtained token via OAuth2!")
                return token
            
            # Step 3: Fallback to browser extraction
            logger.info("🔄 Falling back to browser extraction...")
            return self._extract_from_browser_session()
            
        except Exception as e:
            logger.error(f"❌ Enhanced token extraction failed: {e}")
            return None
    
    def _get_authorization_code(self) -> Optional[str]:
        """Get authorization code by following OAuth2 flow"""
        try:
            logger.info("🔐 Getting authorization code...")
            
            # Build OAuth2 authorization URL (from HAR file)
            auth_params = {
                "client_id": "0oa9je4h93zNQwyuf697",
                "response_type": "code",
                "redirect_uri": "https://savanna.fyber.com/oauth/okta/callback",
                "scope": "openid profile groups",
                "state": "enhanced_state_123",
                "nonce": "enhanced_nonce_456",
                "code_challenge_method": "S256",
                "code_challenge": "test_challenge_123"  # Simplified for testing
            }
            
            auth_url = f"{self.okta_base_url}/oauth2/v1/authorize"
            full_auth_url = f"{auth_url}?{self._build_query_string(auth_params)}"
            
            logger.info(f"🌐 Opening OAuth2 authorization: {full_auth_url}")
            
            # Open browser for user login
            webbrowser.open(full_auth_url)
            
            # Show instructions
            self._show_oauth2_instructions()
            
            # Wait for user to complete login and get code
            auth_code = self._wait_for_authorization_code()
            
            return auth_code
            
        except Exception as e:
            logger.error(f"❌ Error getting authorization code: {e}")
            return None
    
    def _wait_for_authorization_code(self) -> Optional[str]:
        """Wait for user to complete OAuth2 login and extract code"""
        try:
            logger.info("⏳ Waiting for OAuth2 authorization code...")
            
            # Give user time to complete login
            time.sleep(3)
            
            # Try to extract code from various sources
            for attempt in range(10):
                logger.info(f"🔄 Attempt {attempt + 1}/10: Looking for auth code...")
                
                # Method 1: Check if we can access the callback URL
                callback_response = self.session.get(
                    f"{self.savanna_base_url}/oauth/okta/callback",
                    timeout=10,
                    allow_redirects=False
                )
                
                if callback_response.status_code == 200:
                    # Look for authorization code in response
                    code = self._extract_auth_code_from_response(callback_response)
                    if code:
                        logger.info(f"✅ Found authorization code: {code[:10]}...")
                        return code
                
                # Method 2: Check cookies for auth info
                code = self._extract_auth_code_from_cookies()
                if code:
                    return code
                
                # Method 3: Check if we can access protected pages
                if self._can_access_protected_pages():
                    logger.info("✅ Can access protected pages - login may be complete")
                    # Try to extract token directly
                    token = self._extract_token_from_protected_pages()
                    if token:
                        return "LOGIN_COMPLETE"  # Special code to indicate success
                
                # Wait before next attempt
                if attempt < 9:
                    logger.info("⏳ Waiting 5 seconds before next attempt...")
                    time.sleep(5)
            
            logger.warning("⚠️ Could not get authorization code after multiple attempts")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error waiting for authorization code: {e}")
            return None
    
    def _extract_auth_code_from_response(self, response) -> Optional[str]:
        """Extract authorization code from response"""
        try:
            text = response.text
            
            # Look for authorization code in URL parameters
            code_patterns = [
                r'code=([A-Za-z0-9_-]+)',
                r'"code"\s*:\s*"([A-Za-z0-9_-]+)"',
                r'authorization_code["\s]*[:=]\s*["\']([A-Za-z0-9_-]+)["\']'
            ]
            
            for pattern in code_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if len(match) > 10:  # Likely a real auth code
                        logger.info(f"🔍 Found auth code with pattern: {match[:10]}...")
                        return match
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting auth code from response: {e}")
            return None
    
    def _extract_auth_code_from_cookies(self) -> Optional[str]:
        """Extract authorization code from cookies"""
        try:
            cookies = self.session.cookies
            
            # Look for auth-related cookies
            auth_cookies = [
                'auth_code',
                'authorization_code',
                'oauth_code',
                'okta_code'
            ]
            
            for cookie_name in auth_cookies:
                if cookie_name in cookies:
                    cookie_value = cookies[cookie_name]
                    if len(cookie_value) > 10:
                        logger.info(f"🔍 Found auth code in cookie {cookie_name}: {cookie_value[:10]}...")
                        return cookie_value
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting auth code from cookies: {e}")
            return None
    
    def _can_access_protected_pages(self) -> bool:
        """Check if we can access protected pages"""
        try:
            response = self.session.get(
                f"{self.savanna_base_url}/creative-pulling",
                timeout=10,
                allow_redirects=False
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"❌ Error checking protected pages: {e}")
            return False
    
    def _extract_token_from_protected_pages(self) -> Optional[str]:
        """Extract token from protected pages"""
        try:
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
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting token from protected pages: {e}")
            return None
    
    def _exchange_code_for_token(self, auth_code: str) -> Optional[str]:
        """Exchange authorization code for access token"""
        try:
            if auth_code == "LOGIN_COMPLETE":
                logger.info("✅ Login already complete, extracting token directly")
                return self._extract_token_from_protected_pages()
            
            logger.info(f"🔄 Exchanging auth code for token: {auth_code[:10]}...")
            
            # This would require client secret, so we'll skip for now
            logger.info("ℹ️ Code exchange requires client secret (skipping)")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error exchanging code for token: {e}")
            return None
    
    def _extract_from_browser_session(self) -> Optional[str]:
        """Fallback: Extract token from browser session"""
        try:
            logger.info("🌐 Attempting browser session extraction...")
            
            # Try to access protected pages
            token = self._extract_token_from_protected_pages()
            if token:
                return token
            
            # Try to access authentication page
            auth_response = self.session.get(
                f"{self.savanna_base_url}/authentication",
                timeout=10
            )
            
            if auth_response.status_code == 200:
                token = self._extract_token_from_response(auth_response)
                if token:
                    return token
            
            logger.warning("⚠️ Browser session extraction failed")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in browser session extraction: {e}")
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
    
    def _show_oauth2_instructions(self):
        """Show OAuth2 login instructions to user"""
        try:
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            messagebox.showinfo(
                "🔐 OAuth2 Login Required",
                "I've opened your browser to the Okta OAuth2 login page.\n\n"
                "Please:\n"
                "1. Complete the Okta login in your browser\n"
                "2. You'll be redirected to Savanna\n"
                "3. Come back to this app and wait\n\n"
                "The app will automatically detect when login is complete!"
            )
            
            root.destroy()
            
        except Exception as e:
            logger.warning(f"⚠️ Could not show GUI instructions: {e}")
            print("\n🔐 OAUTH2 LOGIN INSTRUCTIONS:")
            print("1. Complete Okta login in your browser")
            print("2. You'll be redirected to Savanna")
            print("3. Come back here and wait...")
    
    def _build_query_string(self, params: Dict[str, str]) -> str:
        """Build query string from parameters"""
        return "&".join([f"{k}={v}" for k, v in params.items()])
    
    def test_enhanced_extraction(self):
        """Test the enhanced token extraction system"""
        print("🧪 Testing Enhanced Token Extraction")
        print("=" * 40)
        
        # Test 1: Check active session
        print("\n📋 TEST 1: CHECK ACTIVE SESSION")
        print("-" * 30)
        active_token = self._check_active_session()
        if active_token:
            print(f"✅ Active token found: {active_token[:20]}...")
            return active_token
        else:
            print("ℹ️ No active session found")
        
        # Test 2: Enhanced OAuth2 extraction
        print("\n🚀 TEST 2: ENHANCED OAUTH2 EXTRACTION")
        print("-" * 35)
        print("This will follow the actual OAuth2 flow...")
        
        token = self.extract_token_enhanced()
        if token:
            print(f"✅ Token extracted successfully: {token[:20]}...")
            return token
        else:
            print("❌ Failed to extract token")
            return None

def main():
    """Main test function"""
    print("🚀 Enhanced Token Extraction Test")
    print("=" * 40)
    
    extractor = EnhancedTokenExtractor()
    token = extractor.test_enhanced_extraction()
    
    if token:
        print(f"\n🎉 SUCCESS! Extracted token: {token[:50]}...")
    else:
        print("\n❌ Token extraction failed")
    
    print("\n✨ Test complete!")

if __name__ == "__main__":
    main()


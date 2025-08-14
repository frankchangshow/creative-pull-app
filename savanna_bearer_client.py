#!/usr/bin/env python3
"""
Savanna Bearer Token Client
Uses the existing bearer token from HAR file to test the API
"""

import requests
import json
import time
import base64
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SavannaBearerClient:
    """Advanced client with automatic JWT token refresh for Savanna API"""
    
    def __init__(self):
        # Load bearer token from config or use default
        self.bearer_token = self.load_savanna_token()
        
        # Savanna API endpoints
        self.savanna_api_url = "https://savanna.fyber.com/creative-pulling"
        self.feathers_auth_url = "https://savanna.fyber.com/authentication"
        
        # Session for making requests
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Token management
        self.token_expiry = None
        self.refresh_threshold = 3600  # Refresh 1 hour before expiry
        
        logger.info("🚀 Advanced Bearer Token Client initialized")
        
        # Check and refresh token if needed
        self._ensure_valid_token()
    
    def load_savanna_token(self):
        """Load Savanna bearer token from config file or prompt user"""
        import configparser
        import os
        
        try:
            # Try to load from config file
            config = configparser.ConfigParser()
            config_paths = [
                "config.ini",  # Current directory
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini"),  # Script directory
                os.path.join(os.path.expanduser("~"), ".creative_pull_app", "config.ini"),  # User home directory
            ]
            
            for config_path in config_paths:
                if os.path.exists(config_path):
                    config.read(config_path)
                    if config.has_section("SAVANNA") and config.has_option("SAVANNA", "bearer_token"):
                        saved_token = config.get("SAVANNA", "bearer_token")
                        if saved_token and saved_token.startswith("eyJ") and len(saved_token.strip()) > 50:
                            logger.info("✅ Using saved Savanna token from config.ini")
                            return saved_token.strip()
                        else:
                            logger.warning(f"⚠️ Token in config is invalid: {saved_token[:20]}...")
                    break
            
            # If no valid token in config, prompt user
            logger.warning("⚠️ No valid Savanna token found, prompting user...")
            return self.prompt_for_savanna_token()
            
        except Exception as e:
            logger.error(f"❌ Error loading Savanna token: {e}")
            return self.prompt_for_savanna_token()
    
    def prompt_for_savanna_token(self):
        """Prompt user to enter Savanna bearer token"""
        try:
            from tkinter import simpledialog, messagebox
            
            # Create a simple dialog for token input
            token = simpledialog.askstring(
                "Savanna Token Required",
                "Please enter your Savanna Bearer Token:\n\n" +
                "You can get this from:\n" +
                "Savanna → User Settings → Access Tokens\n\n" +
                "Token (starts with 'eyJ'):",
                show='*'  # Hide the token input
            )
            
            if token and token.strip().startswith('eyJ') and len(token.strip()) > 50:
                # Ask if user wants to save it
                save_token = messagebox.askyesno(
                    "Save Token",
                    "Would you like to save this token to config.ini for future use?\n\n" +
                    "This will make it easier to run the app next time, but the token " +
                    "will be stored in plain text on your computer."
                )
                
                if save_token:
                    self.save_savanna_token_to_config(token.strip())
                
                return token.strip()
            
            # Return default expired token if user cancels
            logger.warning("⚠️ No token provided, using default (will likely fail)")
            return "eyJhbGciOiJIUzI1NiIsInR5cCI6ImFjY2VzcyJ9.eyJyb2xlcyI6WyJzZSJdLCJ1c2VyIjoiZnJhbmsuY2hhbmdAZGlnaXRhbHR1cmJpbmUuY29tIiwiaWF0IjoxNzU1MDQyNzM0LCJleHAiOjE3NTUwNjQzMzQsImF1ZCI6Imh0dHBzOi8vZnliZXIuY29tIiwiaXNzIjoic2F2YW5uYSIsInN1YiI6InlRNm9OVkJNb0RnS1JjZEgiLCJqdGkiOiIxZDQzOGQwMC02NThkLTQzNDMtOTdiYy0wYmI3Y2UyNWIyNDAifQ._iBIHzmr4xpem1dY_ot88g8QMUxhzN9gr8qjqxCfPMk"
            
        except ImportError:
            # If tkinter is not available, just return the default token
            logger.warning("⚠️ Tkinter not available, using default token")
            return "eyJhbGciOiJIUzI1NiIsInR5cCI6ImFjY2VzcyJ9.eyJyb2xlcyI6WyJzZSJdLCJ1c2VyIjoiZnJhbmsuY2hhbmdAZGlnaXRhbHR1cmJpbmUuY29tIiwiaWF0IjoxNzU1MDQyNzM0LCJleHAiOjE3NTUwNjQzMzQsImF1ZCI6Imh0dHBzOi8vZnliZXIuY29tIiwiaXNzIjoic2F2YW5uYSIsInN1YiI6InlRNm9OVkJNb0RnS1JjZEgiLCJqdGkiOiIxZDQzOGQwMC02NThkLTQzNDMtOTdiYy0wYmI3Y2UyNWIyNDAifQ._iBIHzmr4xpem1dY_ot88g8QMUxhzN9gr8qjqxCfPMk"
    
    def save_savanna_token_to_config(self, token):
        """Save Savanna token to config.ini file"""
        try:
            import configparser
            import os
            
            config = configparser.ConfigParser()
            
            # Try to read existing config from multiple locations
            config_read = False
            config_paths = [
                "config.ini",  # Current directory
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini"),  # Script directory
                os.path.join(os.path.expanduser("~"), ".creative_pull_app", "config.ini"),  # User home directory
            ]
            
            for config_path in config_paths:
                if os.path.exists(config_path):
                    config.read(config_path)
                    config_read = True
                    logger.info(f"✅ Reading existing config from: {config_path}")
                    break
            
            # Add/update SAVANNA section
            if not config.has_section('SAVANNA'):
                config.add_section('SAVANNA')
            
            config.set('SAVANNA', 'bearer_token', token)
            
            # Try to save to multiple locations, prefer user home directory
            save_paths = [
                os.path.join(os.path.expanduser("~"), ".creative_pull_app", "config.ini"),  # User home (preferred)
                "config.ini",  # Current directory
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini"),  # Script directory
            ]
            
            saved = False
            for save_path in save_paths:
                try:
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    with open(save_path, 'w') as configfile:
                        config.write(configfile)
                    
                    logger.info(f"✅ Savanna token saved to: {save_path}")
                    saved = True
                    break
                except Exception as e:
                    logger.warning(f"⚠️ Could not save to {save_path}: {e}")
                    continue
            
            if not saved:
                logger.warning("❌ Warning: Could not save Savanna token to any location")
            
        except Exception as e:
            logger.warning(f"⚠️ Warning: Could not save Savanna token to config.ini: {e}")
    
    def refresh_token_if_needed(self):
        """Enhanced token refresh that checks expiration proactively"""
        try:
            # Check if token is expired or close to expiry
            is_expired, expiry_time = self._is_token_expired(self.bearer_token)
            
            if is_expired:
                logger.warning("🔄 Token is expired, refreshing...")
                return self._refresh_token()
                if new_token and new_token != self.bearer_token:
                    self.bearer_token = new_token
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.bearer_token}'
                    })
                    logger.info("✅ Token refreshed successfully")
                    return True
                else:
                    logger.warning("⚠️ No new token provided")
                    return False
            elif expiry_time and (expiry_time - datetime.now()).total_seconds() <= self.refresh_threshold:
                logger.warning("🔄 Token expires soon, refreshing proactively...")
                return self._refresh_token()
            else:
                logger.info("✅ Token is still valid")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error checking token validity: {e}")
            return False
    
    def _decode_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token to extract payload without verification"""
        try:
            # Split the token into parts
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning("⚠️ Invalid JWT token format")
                return None
            
            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            
            # Decode base64
            decoded = base64.b64decode(payload)
            payload_data = json.loads(decoded.decode('utf-8'))
            
            logger.info(f"🔍 JWT Token decoded successfully")
            logger.info(f"   Issued at: {datetime.fromtimestamp(payload_data.get('iat', 0))}")
            logger.info(f"   Expires at: {datetime.fromtimestamp(payload_data.get('exp', 0))}")
            logger.info(f"   User: {payload_data.get('user', 'Unknown')}")
            logger.info(f"   Roles: {payload_data.get('roles', [])}")
            
            return payload_data
            
        except Exception as e:
            logger.error(f"❌ Error decoding JWT token: {e}")
            return None
    
    def _is_token_expired(self, token: str) -> Tuple[bool, Optional[datetime]]:
        """Check if JWT token is expired or close to expiry"""
        try:
            payload = self._decode_jwt_token(token)
            if not payload:
                return True, None
            
            exp_timestamp = payload.get('exp')
            if not exp_timestamp:
                logger.warning("⚠️ No expiration time in JWT token")
                return True, None
            
            expiry_time = datetime.fromtimestamp(exp_timestamp)
            current_time = datetime.now()
            
            # Check if expired
            if current_time >= expiry_time:
                logger.warning(f"⚠️ Token expired at {expiry_time}")
                return True, expiry_time
            
            # Check if close to expiry (within refresh threshold)
            time_until_expiry = (expiry_time - current_time).total_seconds()
            if time_until_expiry <= self.refresh_threshold:
                logger.warning(f"⚠️ Token expires in {time_until_expiry/3600:.1f} hours, refreshing...")
                return False, expiry_time
            
            logger.info(f"✅ Token valid for {time_until_expiry/3600:.1f} more hours")
            return False, expiry_time
            
        except Exception as e:
            logger.error(f"❌ Error checking token expiration: {e}")
            return True, None
    
    def _ensure_valid_token(self):
        """Ensure we have a valid token, refresh if needed"""
        try:
            is_expired, expiry_time = self._is_token_expired(self.bearer_token)
            
            if is_expired:
                logger.warning("🔄 Token is expired, attempting refresh...")
                self._refresh_token()
            elif expiry_time:
                self.token_expiry = expiry_time
                logger.info(f"✅ Token is valid until {expiry_time}")
                
        except Exception as e:
            logger.error(f"❌ Error ensuring valid token: {e}")
    
    def _refresh_token_feathers(self) -> Optional[str]:
        """Attempt to refresh token using Feathers.js authentication endpoint"""
        try:
            logger.info("🔄 Attempting Feathers.js JWT refresh...")
            
            # Try to refresh using current token
            refresh_data = {
                "strategy": "jwt",
                "accessToken": self.bearer_token
            }
            
            response = self.session.post(
                self.feathers_auth_url,
                json=refresh_data,
                timeout=15
            )
            
            logger.info(f"Feathers refresh status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    new_token = data.get('accessToken')
                    if new_token and new_token != self.bearer_token:
                        logger.info("✅ Feathers.js refresh successful!")
                        return new_token
                    else:
                        logger.warning("⚠️ Feathers refresh returned same token")
                        return None
                except:
                    logger.warning("⚠️ Could not parse Feathers refresh response")
                    return None
            elif response.status_code == 401:
                logger.warning("⚠️ Feathers refresh failed - current token invalid")
                return None
            else:
                logger.warning(f"⚠️ Feathers refresh failed with status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error during Feathers refresh: {e}")
            return None
    
    def _refresh_token(self) -> bool:
        """Attempt multiple token refresh strategies"""
        logger.info("🔄 Starting token refresh process...")
        
        # Strategy 1: Feathers.js JWT refresh
        new_token = self._refresh_token_feathers()
        if new_token:
            self._update_token(new_token)
            return True
        
        # Strategy 2: Prompt user for new token
        logger.warning("🔄 Automatic refresh strategies failed, prompting user...")
        new_token = self.prompt_for_savanna_token()
        if new_token and new_token != self.bearer_token:
            self._update_token(new_token)
            return True
        
        logger.error("❌ All token refresh strategies failed")
        return False
    
    def _update_token(self, new_token: str):
        """Update the client with a new token"""
        logger.info("🔄 Updating client with new token...")
        
        self.bearer_token = new_token
        self.session.headers.update({
            'Authorization': f'Bearer {new_token}'
        })
        
        # Update expiry time
        _, expiry_time = self._is_token_expired(new_token)
        self.token_expiry = expiry_time
        
        # Save to config
        self.save_savanna_token_to_config(new_token)
        
        logger.info("✅ Token updated successfully")
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get detailed information about the current token"""
        try:
            payload = self._decode_jwt_token(self.bearer_token)
            if not payload:
                return {"error": "Could not decode token"}
            
            expiry_time = datetime.fromtimestamp(payload.get('exp', 0))
            issued_time = datetime.fromtimestamp(payload.get('iat', 0))
            current_time = datetime.now()
            
            time_until_expiry = (expiry_time - current_time).total_seconds()
            
            return {
                "user": payload.get('user', 'Unknown'),
                "roles": payload.get('roles', []),
                "issued_at": issued_time.isoformat(),
                "expires_at": expiry_time.isoformat(),
                "time_until_expiry_hours": round(time_until_expiry / 3600, 2),
                "is_expired": time_until_expiry <= 0,
                "needs_refresh": time_until_expiry <= self.refresh_threshold,
                "token_preview": f"{self.bearer_token[:20]}...{self.bearer_token[-20:]}"
            }
            
        except Exception as e:
            return {"error": f"Error getting token info: {e}"}
    
    def smart_post_to_creative_pulling(self, creative_data: Dict[str, Any]):
        """Enhanced post method with automatic token management"""
        logger.info("📤 Smart posting to creative-pulling...")
        
        # Ensure token is valid before posting
        if not self._ensure_valid_token():
            logger.error("❌ Could not obtain valid token")
            return None
        
        # Now post with confidence
        return self.post_to_creative_pulling(creative_data)
    
    def test_authentication_endpoints(self):
        """Test various authentication-related endpoints"""
        logger.info("🔍 Testing authentication endpoints...")
        
        endpoints_to_test = [
            "/authentication",
            "/oauth/okta/authenticate",
            "/oauth/okta/callback"
        ]
        
        for endpoint in endpoints_to_test:
            url = f"https://savanna.fyber.com{endpoint}"
            try:
                response = self.session.get(url, timeout=10)
                logger.info(f"   {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"      ✅ Accessible")
                elif response.status_code == 401:
                    logger.info(f"      🔐 Unauthorized (expected for some endpoints)")
                elif response.status_code == 404:
                    logger.info(f"      ❌ Not found")
                else:
                    logger.info(f"      ⚠️ Status: {response.status_code}")
                    
            except Exception as e:
                logger.info(f"   {endpoint}: ❌ Error - {e}")
    
    def test_connection(self):
        """Test the connection to the API"""
        logger.info("🔍 Testing connection to Savanna API...")
        
        try:
            response = self.session.get(self.savanna_api_url, timeout=10)
            logger.info(f"✅ Connection successful! Status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("🎉 API endpoint accessible with bearer token!")
                try:
                    data = response.json()
                    logger.info(f"📋 Response data: {json.dumps(data, indent=2)}")
                except:
                    logger.info(f"📄 Response text: {response.text[:500]}...")
            else:
                logger.info(f"⚠️ API returned status {response.status_code}")
                logger.info(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
    
    def get_creative_pulling_status(self, creative_id: str = None):
        """Get status from creative-pulling endpoint"""
        logger.info("📊 Getting creative-pulling status...")
        
        params = {}
        if creative_id:
            params['creative_id'] = creative_id
            
        try:
            response = self.session.get(self.savanna_api_url, params=params, timeout=10)
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"✅ Data received: {json.dumps(data, indent=2)}")
                    return data
                except:
                    logger.info(f"📄 Response text: {response.text[:500]}...")
                    return response.text
            else:
                logger.info(f"❌ Error: {response.status_code} - {response.text[:200]}...")
                return None
                
        except Exception as e:
            logger.error(f"❌ Request failed: {e}")
            return None
    
    def post_to_creative_pulling(self, creative_data: Dict[str, Any]):
        """Post creative data to the creative-pulling endpoint"""
        logger.info("📤 Posting to creative-pulling...")
        logger.info(f"Data: {json.dumps(creative_data, indent=2)}")
        
        try:
            response = self.session.post(
                self.savanna_api_url,
                json=creative_data,
                timeout=10
            )
            
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    logger.info(f"✅ Success! Response: {json.dumps(data, indent=2)}")
                    return data
                except:
                    logger.info(f"📄 Response text: {response.text[:500]}...")
                    return response.text
            elif response.status_code == 401:
                logger.warning("🔄 Token expired, attempting to refresh...")
                if self.refresh_token_if_needed():
                    logger.info("🔄 Retrying request with new token...")
                    # Retry the request with the new token
                    response = self.session.post(
                        self.savanna_api_url,
                        json=creative_data,
                        timeout=10
                    )
                    if response.status_code in [200, 201]:
                        try:
                            data = response.json()
                            logger.info(f"✅ Success after token refresh! Response: {json.dumps(data, indent=2)}")
                            return data
                        except:
                            logger.info(f"📄 Response text after refresh: {response.text[:500]}...")
                            return response.text
                    else:
                        logger.info(f"❌ Still failed after token refresh: {response.status_code} - {response.text[:200]}...")
                        return None
                else:
                    logger.error("❌ Could not refresh expired token")
                    return None
            else:
                logger.info(f"❌ Error: {response.status_code} - {response.text[:200]}...")
                return None
                
        except Exception as e:
            logger.error(f"❌ Request failed: {e}")
            return None
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get detailed information about the current bearer token"""
        try:
            # Decode JWT token
            if not self.bearer_token or not self.bearer_token.startswith('eyJ'):
                return {
                    'valid': False,
                    'error': 'Invalid token format'
                }
            
            # Split the token and get the payload
            parts = self.bearer_token.split('.')
            if len(parts) != 3:
                return {
                    'valid': False,
                    'error': 'Invalid JWT format'
                }
            
            # Decode payload
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            
            try:
                decoded = base64.b64decode(payload)
                token_data = json.loads(decoded)
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'Failed to decode token: {str(e)}'
                }
            
            # Extract token information
            current_time = datetime.utcnow()
            
            # Get expiry time
            if 'exp' in token_data:
                expiry_timestamp = token_data['exp']
                expiry_time = datetime.fromtimestamp(expiry_timestamp)
                time_remaining = expiry_time - current_time
                
                # Format time remaining
                if time_remaining.total_seconds() > 0:
                    hours = int(time_remaining.total_seconds() // 3600)
                    minutes = int((time_remaining.total_seconds() % 3600) // 60)
                    time_remaining_str = f"{hours}h {minutes}m"
                else:
                    time_remaining_str = "Expired"
                    expiry_time = "Expired"
            else:
                expiry_time = "Unknown"
                time_remaining_str = "Unknown"
            
            # Get user info
            user = token_data.get('email', token_data.get('sub', 'Unknown'))
            roles = token_data.get('roles', [])
            
            # Determine if token is valid
            is_valid = time_remaining.total_seconds() > 0 if 'exp' in token_data else False
            
            return {
                'valid': is_valid,
                'expires_at': expiry_time.strftime('%Y-%m-%d %H:%M:%S UTC') if isinstance(expiry_time, datetime) else str(expiry_time),
                'time_remaining': time_remaining_str,
                'user': user,
                'roles': roles,
                'issued_at': token_data.get('iat', 'Unknown'),
                'token_type': token_data.get('type', 'Unknown')
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Error parsing token: {str(e)}'
            }
    
    def test_various_endpoints(self):
        """Test various creative-pulling related endpoints"""
        logger.info("🔍 Testing various endpoints...")
        
        endpoints_to_test = [
            "/creative-pulling",
            "/creative-pulling/",
            "/creative-pulling/health",
            "/creative-pulling/status",
            "/creative-pulling/creatives",
            "/creative-pulling/batch"
        ]
        
        for endpoint in endpoints_to_test:
            url = f"https://savanna.fyber.com{endpoint}"
            try:
                response = self.session.get(url, timeout=10)
                logger.info(f"   {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"      ✅ Accessible")
                    try:
                        data = response.json()
                        logger.info(f"      📋 Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    except:
                        logger.info(f"      📄 Text response")
                elif response.status_code == 401:
                    logger.info(f"      🔐 Unauthorized")
                elif response.status_code == 403:
                    logger.info(f"      🚫 Forbidden")
                elif response.status_code == 404:
                    logger.info(f"      ❌ Not found")
                else:
                    logger.info(f"      ⚠️ Status: {response.status_code}")
                    
            except Exception as e:
                logger.info(f"   {endpoint}: ❌ Error - {e}")

def main():
    """Test the bearer token client"""
    logger.info("🚀 Starting Savanna Bearer Token Client Test...")
    
    client = SavannaBearerClient()
    
    # Test 1: Basic connection
    logger.info("\n" + "="*50)
    logger.info("TEST 1: BASIC CONNECTION")
    logger.info("="*50)
    client.test_connection()
    
    # Test 2: Get status
    logger.info("\n" + "="*50)
    logger.info("TEST 2: GET CREATIVE-PULLING STATUS")
    logger.info("="*50)
    client.get_creative_pulling_status()
    
    # Test 3: Test various endpoints
    logger.info("\n" + "="*50)
    logger.info("TEST 3: TEST VARIOUS ENDPOINTS")
    logger.info("="*50)
    client.test_various_endpoints()
    
    # Test 4: Post test data
    logger.info("\n" + "="*50)
    logger.info("TEST 4: POST TEST DATA")
    logger.info("="*50)
    test_data = {
        "creative_id": "test_123",
        "status": "pending",
        "timestamp": time.time(),
        "user": "frank.chang@digitalturbine.com",
        "test": True
    }
    client.post_to_creative_pulling(test_data)
    
    logger.info("\n✨ Bearer token client test complete!")

if __name__ == "__main__":
    main()

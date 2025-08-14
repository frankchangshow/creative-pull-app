#!/usr/bin/env python3
"""
Savanna OAuth Client - Based on HAR Analysis
Handles OAuth 2.0 flow with Okta for Savanna API access
"""

import requests
import json
import time
import base64
import hashlib
import secrets
from urllib.parse import urlencode, parse_qs, urlparse
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SavannaOAuthClient:
    """OAuth 2.0 client for Savanna API authentication via Okta"""
    
    def __init__(self):
        # OAuth Configuration (from HAR analysis)
        self.okta_domain = "digitalturbine.okta.com"
        self.client_id = "0oa9je4h93zNQwyuf697"
        self.redirect_uri = "https://savanna.fyber.com/oauth/okta/callback"
        self.scope = "openid profile groups"
        
        # OAuth endpoints
        self.auth_endpoint = f"https://{self.okta_domain}/oauth2/v1/authorize"
        self.token_endpoint = f"https://{self.okta_domain}/oauth2/v1/token"
        
        # Savanna API endpoint
        self.savanna_api_url = "https://savanna.fyber.com/creative-pulling"
        
        # Session for making requests
        self.session = requests.Session()
        
        # Token storage
        self.access_token = None
        self.token_expires_at = None
        
        # PKCE parameters
        self.code_verifier = None
        self.code_challenge = None
        
    def generate_pkce_params(self):
        """Generate PKCE code verifier and challenge"""
        # Generate random code verifier
        self.code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge
        challenge = hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
        self.code_challenge = base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')
        
        logger.info("PKCE parameters generated")
        return self.code_verifier, self.code_challenge
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate authorization URL for OAuth 2.0 Authorization Code flow with PKCE
        
        Args:
            state: Optional state parameter for security
            
        Returns:
            Authorization URL to redirect user to
        """
        if not state:
            state = base64.b64encode(str(time.time()).encode()).decode()
        
        # Generate PKCE parameters
        self.generate_pkce_params()
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': self.scope,
            'redirect_uri': self.redirect_uri,
            'state': state,
            'response_mode': 'query',
            'code_challenge_method': 'S256',
            'code_challenge': self.code_challenge
        }
        
        auth_url = f"{self.auth_endpoint}?{urlencode(params)}"
        logger.info(f"Authorization URL generated: {auth_url}")
        return auth_url
    
    def exchange_code_for_token(self, authorization_code: str, state: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        
        Args:
            authorization_code: Authorization code from Okta
            state: State parameter for verification
            
        Returns:
            Token response containing access_token
        """
        token_data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'code_verifier': self.code_verifier
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        try:
            response = self.session.post(
                self.token_endpoint,
                data=token_data,
                headers=headers
            )
            response.raise_for_status()
            
            token_response = response.json()
            self._store_tokens(token_response)
            
            logger.info("Successfully exchanged authorization code for tokens")
            return token_response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to exchange code for token: {e}")
            raise
    
    def _store_tokens(self, token_response: Dict[str, Any]):
        """Store tokens from response"""
        self.access_token = token_response.get('access_token')
        
        # Calculate expiration time (default to 1 hour if not provided)
        expires_in = token_response.get('expires_in', 3600)
        self.token_expires_at = time.time() + expires_in
        
        logger.info(f"Tokens stored, expires in {expires_in} seconds")
    
    def is_token_valid(self) -> bool:
        """Check if current access token is still valid"""
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Add 60 second buffer
        return time.time() < (self.token_expires_at - 60)
    
    def make_savanna_request(self, 
                           method: str = 'GET',
                           endpoint: str = '',
                           data: Dict[str, Any] = None,
                           params: Dict[str, Any] = None) -> requests.Response:
        """
        Make authenticated request to Savanna API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (appended to base URL)
            data: Request body data
            params: Query parameters
            
        Returns:
            HTTP response
        """
        if not self.is_token_valid():
            raise ValueError("No valid access token available. Please authenticate first.")
        
        url = f"{self.savanna_api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )
            
            logger.info(f"Made {method} request to {url}")
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def post_to_creative_pulling(self, creative_data: Dict[str, Any]) -> requests.Response:
        """
        Post creative data to the creative-pulling endpoint
        
        Args:
            creative_data: Creative data to post
            
        Returns:
            HTTP response
        """
        return self.make_savanna_request(
            method='POST',
            endpoint='',
            data=creative_data
        )
    
    def get_creative_pulling_status(self, creative_id: str = None) -> requests.Response:
        """
        Get status from creative-pulling endpoint
        
        Args:
            creative_id: Optional creative ID to filter by
            
        Returns:
            HTTP response
        """
        params = {}
        if creative_id:
            params['creative_id'] = creative_id
            
        return self.make_savanna_request(
            method='GET',
            endpoint='',
            params=params
        )

class SavannaDiscoveryClient:
    """Client to discover Savanna API authentication and structure"""
    
    def __init__(self, base_url: str = "https://savanna.fyber.com"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.discovered_auth_methods = []
        self.api_structure = {}
        
    def test_common_auth_methods(self):
        """Test common authentication methods"""
        logger.info("🔍 Testing common authentication methods...")
        
        # Test 1: No authentication
        logger.info("Testing: No authentication")
        response = self.test_endpoint("/creative-pulling", method="GET")
        self.analyze_response(response, "no_auth")
        
        # Test 2: Basic Auth with common credentials
        logger.info("Testing: Basic Auth with common credentials")
        test_credentials = [
            ("admin", "admin"),
            ("user", "password"),
            ("test", "test"),
            ("api", "api"),
            ("creative", "creative")
        ]
        
        for username, password in test_credentials:
            response = self.test_basic_auth("/creative-pulling", username, password)
            if response and response.status_code != 401:  # Not unauthorized
                self.analyze_response(response, f"basic_auth_{username}")
        
        # Test 3: API Key in headers
        logger.info("Testing: API Key in headers")
        common_api_keys = ["X-API-Key", "X-Key", "Authorization", "X-Auth-Token"]
        for header_name in common_api_keys:
            response = self.test_api_key_header("/creative-pulling", header_name, "test_key")
            if response and response.status_code != 401:
                self.analyze_response(response, f"api_key_{header_name}")
        
        # Test 4: Bearer token (empty)
        logger.info("Testing: Bearer token (empty)")
        response = self.test_bearer_token("/creative-pulling", "")
        self.analyze_response(response, "bearer_empty")
        
        # Test 5: Check for public endpoints
        logger.info("Testing: Public endpoints")
        self.discover_public_endpoints()
        
    def test_endpoint(self, endpoint: str, method: str = "GET", **kwargs) -> requests.Response:
        """Test an endpoint with given parameters"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            return response
        except Exception as e:
            logger.error(f"Error testing {url}: {e}")
            return None
    
    def test_basic_auth(self, endpoint: str, username: str, password: str) -> requests.Response:
        """Test basic authentication"""
        return self.test_endpoint(endpoint, auth=(username, password))
    
    def test_api_key_header(self, endpoint: str, header_name: str, api_key: str) -> requests.Response:
        """Test API key in header"""
        headers = {header_name: api_key}
        return self.test_endpoint(endpoint, headers=headers)
    
    def test_bearer_token(self, endpoint: str, token: str) -> requests.Response:
        """Test bearer token authentication"""
        headers = {"Authorization": f"Bearer {token}"}
        return self.test_endpoint(endpoint, headers=headers)
    
    def analyze_response(self, response: requests.Response, auth_method: str):
        """Analyze API response for clues"""
        if not response:
            return
            
        logger.info(f"🔍 {auth_method.upper()} - Status: {response.status_code}")
        
        # Check for authentication hints in response
        if response.status_code == 401:
            auth_header = response.headers.get('WWW-Authenticate', '')
            if auth_header:
                logger.info(f"   🔐 Authentication required: {auth_header}")
                
        elif response.status_code == 403:
            logger.info(f"   🚫 Forbidden - might need different permissions")
            
        elif response.status_code == 200:
            logger.info(f"   ✅ Success! Endpoint accessible")
            self.discovered_auth_methods.append(auth_method)
            
            # Try to parse response for API structure
            try:
                data = response.json()
                self.analyze_api_structure(data, auth_method)
            except:
                logger.info(f"   📄 Response is not JSON: {response.text[:200]}...")
                
        elif response.status_code == 404:
            logger.info(f"   ❌ Endpoint not found")
            
        # Check for rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', 'unknown')
            logger.info(f"   ⏰ Rate limited. Retry after: {retry_after}")
    
    def analyze_api_structure(self, data: Any, auth_method: str):
        """Analyze API response structure"""
        if isinstance(data, dict):
            logger.info(f"   📋 API Structure ({auth_method}):")
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    logger.info(f"      {key}: {type(value).__name__}")
                else:
                    logger.info(f"      {key}: {value}")
        elif isinstance(data, list):
            logger.info(f"   📋 API returns list with {len(data)} items")
            if data and isinstance(data[0], dict):
                logger.info(f"      Sample keys: {list(data[0].keys())}")
    
    def discover_public_endpoints(self):
        """Try to discover public endpoints"""
        common_endpoints = [
            "/",
            "/health",
            "/status",
            "/api",
            "/docs",
            "/swagger",
            "/openapi",
            "/creative-pulling/health",
            "/creative-pulling/status"
        ]
        
        for endpoint in common_endpoints:
            response = self.test_endpoint(endpoint)
            if response and response.status_code == 200:
                logger.info(f"   🌐 Public endpoint found: {endpoint}")
    
    def test_creative_pulling_endpoints(self):
        """Test various creative-pulling endpoints"""
        logger.info("🔍 Testing creative-pulling specific endpoints...")
        
        endpoints_to_test = [
            "/creative-pulling",
            "/creative-pulling/",
            "/creative-pulling/health",
            "/creative-pulling/status",
            "/creative-pulling/creatives",
            "/creative-pulling/batch"
        ]
        
        for endpoint in endpoints_to_test:
            response = self.test_endpoint(endpoint)
            if response:
                logger.info(f"   {endpoint}: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"      ✅ Accessible")
                elif response.status_code == 401:
                    logger.info(f"      🔐 Requires authentication")
                elif response.status_code == 404:
                    logger.info(f"      ❌ Not found")
    
    def generate_auth_hypotheses(self):
        """Generate hypotheses about authentication based on findings"""
        logger.info("🤔 Generating authentication hypotheses...")
        
        if not self.discovered_auth_methods:
            logger.info("   ❌ No successful authentication methods found")
            logger.info("   💡 Possible reasons:")
            logger.info("      - All endpoints require authentication")
            logger.info("   💡 Next steps:")
            logger.info("      - Use Chrome DevTools to capture OAuth flow")
            logger.info("      - Look for token refresh endpoints")
            logger.info("      - Check for session management")
        else:
            logger.info("   ✅ Successful authentication methods:")
            for method in self.discovered_auth_methods:
                logger.info(f"      - {method}")
        
        logger.info("   🔍 Next steps:")
        logger.info("      - Check if you need VPN access")
        logger.info("      - Look for API documentation in company intranet")
        logger.info("      - Ask colleagues about API access")
        logger.info("      - Check if there's a staging/test environment")

def main():
    """Run the discovery client and OAuth flow"""
    logger.info("🚀 Starting Savanna API Discovery and OAuth Flow...")
    
    # Step 1: Run discovery
    logger.info("\n" + "="*50)
    logger.info("STEP 1: API DISCOVERY")
    logger.info("="*50)
    
    discovery_client = SavannaDiscoveryClient()
    
    # Test various authentication methods
    discovery_client.test_common_auth_methods()
    
    # Test creative-pulling specific endpoints
    discovery_client.test_creative_pulling_endpoints()
    
    # Generate hypotheses
    discovery_client.generate_auth_hypotheses()
    
    # Step 2: OAuth Flow
    logger.info("\n" + "="*50)
    logger.info("STEP 2: OAUTH FLOW")
    logger.info("="*50)
    
    oauth_client = SavannaOAuthClient()
    
    # Generate authorization URL
    auth_url = oauth_client.get_authorization_url()
    logger.info(f"🔑 Authorization URL: {auth_url}")
    
    logger.info("\n📋 Next Steps:")
    logger.info("1. Visit the authorization URL above")
    logger.info("2. Login with your Okta credentials")
    logger.info("3. Authorize the application")
    logger.info("4. Copy the authorization code from the redirect URL")
    logger.info("5. Use the code to get an access token")
    logger.info("6. Test API calls to creative-pulling")
    
    logger.info("\n✨ Discovery and OAuth setup complete!")

if __name__ == "__main__":
    main()

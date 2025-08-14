#!/usr/bin/env python3
"""
Quick HAR Token Extractor - Command Line Version
Extract and update Savanna bearer tokens from HAR files quickly
"""

import json
import re
import os
import configparser
import sys
from typing import Dict, Any, List
import argparse
from datetime import datetime

def extract_tokens_from_har(har_file_path: str) -> Dict[str, Any]:
    """Extract tokens from HAR file"""
    try:
        print(f"🔍 Analyzing HAR file: {har_file_path}")
        
        with open(har_file_path, 'r', encoding='utf-8') as f:
            har_data = json.load(f)
        
        tokens_found = {
            'bearer_tokens': [],
            'oauth_codes': [],
            'auth_urls': [],
            'callback_urls': []
        }
        
        # Extract bearer tokens
        bearer_pattern = r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'
        
        for entry in har_data.get('log', {}).get('entries', []):
            # Check request headers
            if 'request' in entry:
                headers = entry['request'].get('headers', [])
                for header in headers:
                    if header.get('name', '').lower() == 'authorization':
                        auth_value = header.get('value', '')
                        if 'Bearer ' in auth_value:
                            token = auth_value.replace('Bearer ', '')
                            if re.match(bearer_pattern, token):
                                tokens_found['bearer_tokens'].append({
                                    'token': token,
                                    'url': entry['request'].get('url', ''),
                                    'method': entry['request'].get('method', ''),
                                    'timestamp': entry.get('startedDateTime', ''),
                                    'source': 'header'
                                })
            
            # Check response bodies for tokens
            if 'response' in entry:
                content = entry['response'].get('content', {})
                if 'text' in content:
                    text_content = content['text']
                    
                    # Look for bearer tokens in response text
                    bearer_matches = re.findall(bearer_pattern, text_content)
                    for token in bearer_matches:
                        if token not in [t['token'] for t in tokens_found['bearer_tokens']]:
                            tokens_found['bearer_tokens'].append({
                                'token': token,
                                'url': entry['request'].get('url', ''),
                                'method': entry['request'].get('method', ''),
                                'timestamp': entry.get('startedDateTime', ''),
                                'source': 'response_body'
                            })
                    
                    # Look for access_token in URLs or response
                    access_token_pattern = r'access_token=([a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)'
                    access_tokens = re.findall(access_token_pattern, text_content)
                    for token in access_tokens:
                        if token not in [t['token'] for t in tokens_found['bearer_tokens']]:
                            tokens_found['bearer_tokens'].append({
                                'token': token,
                                'url': entry['request'].get('url', ''),
                                'method': entry['request'].get('method', ''),
                                'timestamp': entry.get('startedDateTime', ''),
                                'source': 'access_token'
                            })
            
            # Check URLs for OAuth flows
            url = entry['request'].get('url', '')
            if 'oauth2/v1/authorize' in url:
                tokens_found['auth_urls'].append(url)
            elif 'oauth/okta/callback' in url:
                tokens_found['callback_urls'].append(url)
        
        # Remove duplicates
        unique_tokens = []
        seen_tokens = set()
        for token_info in tokens_found['bearer_tokens']:
            if token_info['token'] not in seen_tokens:
                unique_tokens.append(token_info)
                seen_tokens.add(token_info['token'])
        
        tokens_found['bearer_tokens'] = unique_tokens
        
        print(f"✅ Found {len(tokens_found['bearer_tokens'])} bearer tokens")
        print(f"✅ Found {len(tokens_found['oauth_codes'])} OAuth codes")
        
        return tokens_found
        
    except Exception as e:
        print(f"❌ Error extracting tokens from HAR: {e}")
        return {}

def validate_token(token: str) -> Dict[str, Any]:
    """Validate a bearer token by making a test API call"""
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # Test with a simple API endpoint
        test_url = "https://savanna.fyber.com/ad-networks"
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return {
                'valid': True,
                'status_code': response.status_code,
                'message': 'Token is valid and working'
            }
        else:
            return {
                'valid': False,
                'status_code': response.status_code,
                'message': f'Token returned status {response.status_code}'
            }
            
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'message': 'Error testing token'
        }

def decode_jwt_payload(token: str) -> Dict[str, Any]:
    """Decode JWT token to show user info and expiration"""
    try:
        import base64
        
        # Split the token
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        
        # Decode payload
        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        
        decoded = base64.b64decode(payload)
        token_data = json.loads(decoded)
        
        return token_data
        
    except Exception as e:
        print(f"❌ Error decoding JWT: {e}")
        return {}

def copy_to_clipboard(token: str) -> bool:
    """Copy token to clipboard"""
    try:
        import subprocess
        import platform
        
        system = platform.system()
        
        if system == "Darwin":  # macOS
            subprocess.run(['pbcopy'], input=token.encode(), check=True)
        elif system == "Linux":
            subprocess.run(['xclip', '-selection', 'clipboard'], input=token.encode(), check=True)
        elif system == "Windows":
            subprocess.run(['clip'], input=token.encode(), check=True)
        else:
            print(f"⚠️ Clipboard not supported on {system}")
            return False
        
        print(f"✅ Token copied to clipboard!")
        return True
        
    except Exception as e:
        print(f"❌ Error copying to clipboard: {e}")
        return False

def update_config(token: str, config_file: str = "config.ini") -> bool:
    """Update config.ini with new token"""
    try:
        config = configparser.ConfigParser()
        
        # Read existing config if it exists
        if os.path.exists(config_file):
            config.read(config_file)
        
        # Ensure SAVANNA section exists
        if 'SAVANNA' not in config:
            config.add_section('SAVANNA')
        
        # Update the bearer token
        config['SAVANNA']['bearer_token'] = token
        
        # Write back to file
        with open(config_file, 'w') as configfile:
            config.write(config_file)
        
        print(f"✅ Updated {config_file} with new token")
        return True
        
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Quick HAR Token Extractor')
    parser.add_argument('har_file', help='Path to HAR file')
    parser.add_argument('--config', '-c', default='config.ini', help='Config file path (default: config.ini)')
    parser.add_argument('--validate', '-v', action='store_true', help='Validate tokens before updating')
    parser.add_argument('--auto-update', '-a', action='store_true', help='Automatically update config with first valid token')
    parser.add_argument('--copy', '-c', action='store_true', help='Copy first valid token to clipboard')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.har_file):
        print(f"❌ HAR file not found: {args.har_file}")
        sys.exit(1)
    
    print("🚀 Quick HAR Token Extractor")
    print("=" * 50)
    
    # Extract tokens
    tokens_found = extract_tokens_from_har(args.har_file)
    
    if not tokens_found.get('bearer_tokens'):
        print("❌ No bearer tokens found in HAR file")
        sys.exit(1)
    
    print("\n🔐 Found Bearer Tokens:")
    print("-" * 50)
    
    valid_tokens = []
    
    for i, token_info in enumerate(tokens_found['bearer_tokens'], 1):
        token = token_info['token']
        source = token_info.get('source', 'unknown')
        url = token_info.get('url', '')[:60] + "..." if len(token_info.get('url', '')) > 60 else token_info.get('url', '')
        
        print(f"\n{i}. Token Preview: {token[:20]}...{token[-20:]}")
        print(f"   Source: {source}")
        print(f"   URL: {url}")
        
        # Decode JWT payload
        payload = decode_jwt_payload(token)
        if payload:
            if 'user' in payload:
                print(f"   User: {payload['user']}")
            if 'roles' in payload:
                print(f"   Roles: {', '.join(payload['roles'])}")
            if 'iat' in payload:
                issued = datetime.fromtimestamp(payload['iat']).strftime('%Y-%m-%d %H:%M:%S UTC')
                print(f"   Issued: {issued}")
            if 'exp' in payload:
                expires = datetime.fromtimestamp(payload['exp']).strftime('%Y-%m-%d %H:%M:%S UTC')
                print(f"   Expires: {expires}")
        
        # Validate token if requested
        if args.validate:
            print("   Validating token...")
            validation = validate_token(token)
            if validation.get('valid', False):
                print(f"   ✅ Status: Valid (Status: {validation['status_code']})")
                valid_tokens.append(token_info)
            else:
                print(f"   ❌ Status: Invalid - {validation.get('message', 'Unknown error')}")
        else:
            # Assume valid if not validating
            valid_tokens.append(token_info)
    
    print(f"\n📊 Summary:")
    print(f"   Total tokens found: {len(tokens_found['bearer_tokens'])}")
    print(f"   Valid tokens: {len(valid_tokens)}")
    
    if args.copy and valid_tokens:
        # Copy the first valid token to clipboard
        selected_token = valid_tokens[0]['token']
        print(f"\n📋 Copying first valid token to clipboard...")
        
        if copy_to_clipboard(selected_token):
            print(f"✅ Token copied: {selected_token[:30]}...{selected_token[-30:]}")
        else:
            print(f"❌ Failed to copy token")
            sys.exit(1)
    
    elif args.auto_update and valid_tokens:
        # Use the first valid token
        selected_token = valid_tokens[0]['token']
        print(f"\n🔄 Auto-updating config with first valid token...")
        
        if update_config(selected_token, args.config):
            print(f"✅ Successfully updated {args.config}")
            print(f"💡 Please restart your main app for changes to take effect")
        else:
            print(f"❌ Failed to update config")
            sys.exit(1)
    
    elif not args.auto_update and not args.copy and valid_tokens:
        print(f"\n💡 Available actions:")
        print(f"   Copy to clipboard: python3 quick_har_extract.py {args.har_file} --copy")
        print(f"   Update config: python3 quick_har_extract.py {args.har_file} --auto-update")
        print(f"   Or use the GUI version: python3 har_token_extractor.py")
        
        # Show full tokens for easy copying
        if valid_tokens:
            print(f"\n📋 Full Tokens (for copying):")
            print("-" * 50)
            for i, token_info in enumerate(valid_tokens, 1):
                print(f"\n{i}. Full Token:")
                print(f"   {token_info['token']}")
                print(f"   Source: {token_info.get('source', 'unknown')}")
                print(f"   URL: {token_info.get('url', '')[:80]}...")

if __name__ == "__main__":
    main()

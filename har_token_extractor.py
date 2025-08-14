#!/usr/bin/env python3
"""
HAR File Token Extractor
Extracts fresh Savanna bearer tokens from HAR files and updates config.ini
"""

import json
import re
import os
import configparser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HARTokenExtractor:
    """Extract tokens from HAR files and update configuration"""
    
    def __init__(self):
        self.savanna_base_url = "https://savanna.fyber.com"
        self.config_file = "config.ini"
        
    def extract_tokens_from_har(self, har_file_path: str) -> Dict[str, Any]:
        """Extract all relevant tokens from HAR file"""
        try:
            logger.info(f"🔍 Analyzing HAR file: {har_file_path}")
            
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
                                        'timestamp': entry.get('startedDateTime', '')
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
                        
                        # Look for OAuth authorization codes
                        oauth_code_pattern = r'code=([a-zA-Z0-9_-]+)'
                        oauth_codes = re.findall(oauth_code_pattern, text_content)
                        for code in oauth_codes:
                            if code not in tokens_found['oauth_codes']:
                                tokens_found['oauth_codes'].append(code)
                        
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
            
            logger.info(f"✅ Found {len(tokens_found['bearer_tokens'])} bearer tokens")
            logger.info(f"✅ Found {len(tokens_found['oauth_codes'])} OAuth codes")
            
            return tokens_found
            
        except Exception as e:
            logger.error(f"❌ Error extracting tokens from HAR: {e}")
            return {}
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a bearer token by making a test API call"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Test with a simple API endpoint
            test_url = f"{self.savanna_base_url}/ad-networks"
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
    
    def update_config(self, token: str) -> bool:
        """Update config.ini with new token"""
        try:
            config = configparser.ConfigParser()
            
            # Read existing config if it exists
            if os.path.exists(self.config_file):
                config.read(self.config_file)
            
            # Ensure SAVANNA section exists
            if 'SAVANNA' not in config:
                config.add_section('SAVANNA')
            
            # Update the bearer token
            config['SAVANNA']['bearer_token'] = token
            
            # Write back to file
            with open(self.config_file, 'w') as configfile:
                config.write(configfile)
            
            logger.info(f"✅ Updated {self.config_file} with new token")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating config: {e}")
            return False
    
    def decode_jwt_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token to show user info and expiration"""
        try:
            import base64
            
            # Split the token
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            
            decoded = base64.b64decode(payload)
            token_data = json.loads(decoded)
            
            return token_data
            
        except Exception as e:
            logger.error(f"❌ Error decoding JWT: {e}")
            return None

class HARTokenExtractorGUI:
    """GUI for HAR token extraction"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("HAR Token Extractor - Savanna")
        self.root.geometry("800x600")
        
        self.extractor = HARTokenExtractor()
        self.current_har_file = None
        self.extracted_tokens = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔍 HAR Token Extractor", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="HAR File Selection", padding="15")
        file_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.file_label = ttk.Label(file_frame, text="No HAR file selected")
        self.file_label.pack(side=tk.LEFT, padx=(0, 10))
        
        browse_button = ttk.Button(file_frame, text="Browse HAR File", command=self.browse_har_file)
        browse_button.pack(side=tk.RIGHT)
        
        # Extract button
        extract_button = ttk.Button(main_frame, text="🔍 Extract Tokens", command=self.extract_tokens, width=20)
        extract_button.pack(pady=(0, 20))
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Extracted Tokens", padding="15")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for tokens
        columns = ('Token Preview', 'Source', 'URL', 'Valid', 'Actions')
        self.token_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=10)
        
        # Configure columns
        for col in columns:
            self.token_tree.heading(col, text=col)
            if col == 'Actions':
                self.token_tree.column(col, width=120)
            else:
                self.token_tree.column(col, width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.token_tree.yview)
        self.token_tree.configure(yscrollcommand=scrollbar.set)
        
        self.token_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click event for token details
        self.token_tree.bind('<Double-1>', self.on_token_double_click)
        
        # Status bar
        self.status_label = ttk.Label(main_frame, text="Ready to extract tokens from HAR file")
        self.status_label.pack(pady=(10, 0))
    
    def browse_har_file(self):
        """Browse for HAR file"""
        file_path = filedialog.askopenfilename(
            title="Select HAR File",
            filetypes=[("HAR files", "*.har"), ("All files", "*.*")]
        )
        
        if file_path:
            self.current_har_file = file_path
            self.file_label.config(text=f"Selected: {os.path.basename(file_path)}")
            self.status_label.config(text=f"Ready to extract from: {os.path.basename(file_path)}")
    
    def extract_tokens(self):
        """Extract tokens from selected HAR file"""
        if not self.current_har_file:
            messagebox.showwarning("Warning", "Please select a HAR file first")
            return
        
        try:
            self.status_label.config(text="Extracting tokens...")
            self.root.update()
            
            # Extract tokens
            self.extracted_tokens = self.extractor.extract_tokens_from_har(self.current_har_file)
            
            # Clear existing items
            for item in self.token_tree.get_children():
                self.token_tree.delete(item)
            
            # Add tokens to treeview
            for token_info in self.extracted_tokens.get('bearer_tokens', []):
                token = token_info['token']
                preview = f"{token[:20]}...{token[-20:]}"
                source = token_info.get('source', 'header')
                url = token_info.get('url', '')[:50] + "..." if len(token_info.get('url', '')) > 50 else token_info.get('url', '')
                
                # Validate token
                validation = self.extractor.validate_token(token)
                valid_status = "✅ Valid" if validation.get('valid', False) else "❌ Invalid"
                
                # Insert into treeview
                item = self.token_tree.insert('', 'end', values=(preview, source, url, valid_status, "Double-click for details"))
                
                # Store full token info
                self.token_tree.set(item, 'Actions', "Double-click for details")
            
            self.status_label.config(text=f"Extracted {len(self.extracted_tokens.get('bearer_tokens', []))} tokens")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract tokens: {str(e)}")
            self.status_label.config(text="Error extracting tokens")
    
    def on_token_double_click(self, event):
        """Handle double-click on token"""
        selection = self.token_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.token_tree.item(item, 'values')
        token_preview = values[0]
        
        # Find the full token
        for token_info in self.extracted_tokens.get('bearer_tokens', []):
            if f"{token_info['token'][:20]}...{token_info['token'][-20:]}" == token_preview:
                token = token_info['token']
                
                # Show token details
                self.show_token_details(token, token_info)
                break
    
    def show_token_details(self, token: str, token_info: Dict[str, Any]):
        """Show detailed token information and offer to use it"""
        # Decode JWT to show user info
        payload = self.extractor.decode_jwt_payload(token)
        
        details_window = tk.Toplevel(self.root)
        details_window.title("Token Details")
        details_window.geometry("600x400")
        details_window.transient(self.root)
        details_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(details_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Token preview
        ttk.Label(main_frame, text="🔐 Token Details", font=("Arial", 14, "bold")).pack(pady=(0, 20))
        
        # Token preview
        ttk.Label(main_frame, text=f"Token: {token[:30]}...{token[-30:]}", 
                 font=("Arial", 10, "bold"), foreground="blue").pack(anchor=tk.W, pady=(0, 10))
        
        # Source info
        ttk.Label(main_frame, text=f"Source: {token_info.get('source', 'Unknown')}").pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(main_frame, text=f"URL: {token_info.get('url', 'Unknown')}").pack(anchor=tk.W, pady=(0, 5))
        
        # JWT payload info
        if payload:
            ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
            ttk.Label(main_frame, text="JWT Payload:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
            
            if 'user' in payload:
                ttk.Label(main_frame, text=f"User: {payload['user']}").pack(anchor=tk.W, pady=(0, 5))
            if 'roles' in payload:
                ttk.Label(main_frame, text=f"Roles: {', '.join(payload['roles'])}").pack(anchor=tk.W, pady=(0, 5))
            if 'iat' in payload:
                issued = datetime.fromtimestamp(payload['iat']).strftime('%Y-%m-%d %H:%M:%S UTC')
                ttk.Label(main_frame, text=f"Issued: {issued}").pack(anchor=tk.W, pady=(0, 5))
            if 'exp' in payload:
                expires = datetime.fromtimestamp(payload['exp']).strftime('%Y-%m-%d %H:%M:%S UTC')
                ttk.Label(main_frame, text=f"Expires: {expires}").pack(anchor=tk.W, pady=(0, 5))
        
        # Validation
        validation = self.extractor.validate_token(token)
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        if validation.get('valid', False):
            ttk.Label(main_frame, text="✅ Token is valid and working!", 
                     font=("Arial", 11, "bold"), foreground="green").pack(pady=(0, 10))
        else:
            ttk.Label(main_frame, text=f"❌ Token validation failed: {validation.get('message', 'Unknown error')}", 
                     font=("Arial", 11, "bold"), foreground="red").pack(pady=(0, 10))
        
        # Copy token button
        copy_button = ttk.Button(main_frame, text="📋 Copy Token", 
                                command=lambda: self.copy_token_to_clipboard(token))
        copy_button.pack(pady=(0, 10))
        
        # Close button
        ttk.Button(main_frame, text="Close", command=details_window.destroy).pack()
    
    def copy_token_to_clipboard(self, token: str):
        """Copy token to clipboard"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(token)
            messagebox.showinfo("Copied!", f"✅ Token copied to clipboard!\n\nToken: {token[:30]}...{token[-30:]}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy token: {str(e)}")
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        try:
            # Get the item under cursor
            item = self.token_tree.identify_row(event.y)
            if not item:
                return
            
            # Select the item
            self.token_tree.selection_set(item)
            
            # Get token info
            values = self.token_tree.item(item, 'values')
            token_preview = values[0]
            
            # Find the full token
            token = None
            for token_info in self.extracted_tokens.get('bearer_tokens', []):
                if f"{token_info['token'][:20]}...{token_info['token'][-20:]}" == token_preview:
                    token = token_info['token']
                    break
            
            if token:
                # Create context menu
                context_menu = tk.Menu(self.root, tearoff=0)
                context_menu.add_command(label="📋 Copy Token", 
                                       command=lambda: self.copy_token_to_clipboard(token))
                context_menu.add_command(label="🔍 View Details", 
                                       command=lambda: self.show_token_details(token, 
                                           next(t for t in self.extracted_tokens.get('bearer_tokens', []) 
                                                if t['token'] == token)))
                context_menu.add_separator()
                context_menu.add_command(label="💾 Use Token", 
                                       command=lambda: self.use_token(token, None))
                
                # Show menu at cursor position
                context_menu.tk_popup(event.x_root, event.y_root)
                
        except Exception as e:
            print(f"Error showing context menu: {e}")
    
    def use_token(self, token: str, window):
        """Use the selected token"""
        try:
            # Update config
            if self.extractor.update_config(token):
                messagebox.showinfo("Success", 
                    "✅ Token updated successfully!\n\n"
                    "The new token has been saved to config.ini.\n"
                    "Please restart your main app for changes to take effect.")
                window.destroy()
            else:
                messagebox.showerror("Error", "Failed to update config file")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to use token: {str(e)}")
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()

def main():
    """Main function"""
    print("🚀 Starting HAR Token Extractor...")
    
    # Check if config.ini exists
    if not os.path.exists("config.ini"):
        print("⚠️ Warning: config.ini not found. Will create it when updating tokens.")
    
    # Start GUI
    app = HARTokenExtractorGUI()
    app.run()

if __name__ == "__main__":
    main()

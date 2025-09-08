#!/usr/bin/env python3
"""
Creative Previewer App - pywebview Version
Uses real browser engine for full MRAID, VAST video, and display ad support
"""

import sys
import os
import json
import tempfile
import webbrowser
import time
from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
# import webview  # Removed due to threading issues on macOS
from databricks import sql
import xml.etree.ElementTree as ET
import configparser

import html
import re
import requests
from utils.vast_utils import (
    extract_vast_url as util_extract_vast_url,
    extract_vast_click_through as util_extract_vast_click,
    get_inline_vast_xml_from_markup as util_get_inline_vast_xml,
)

# Import the Savanna bearer client for save functionality
from savanna_bearer_client import SavannaBearerClient

# Configuration
DATABRICKS_SERVER_HOSTNAME = "3218046436603353.3.gcp.databricks.com"
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/41872fc0c36b8259"
DATABRICKS_TABLE_NAME = "prod_atlas_datalake.pso_sandbox.sampled_ads_persistent"
DATABRICKS_WORKSPACE_URL = "https://3218046436603353.3.gcp.databricks.com"
JOB_ID = 366113680363745  # Creative Pull GCS Job
CREATIVE_PULLING_TABLE = "prod_inneractive_engines_db.inneractive_db_1_8.creative_pulling"

class CreativePreviewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Creative Pull App - Databricks Integration")
        self.root.geometry("1400x900")
        
        # Initialize variables
        self.creatives = []
        self.current_creative = None
        self.current_markup = None
        # Load token via externalized config loader
        from config.app_config import load_configuration
        self.access_token = load_configuration()
        
        # Initialize Savanna client
        self._savanna_token_info_shown = False
        try:
            from savanna_bearer_client import SavannaBearerClient
            self.savanna_client = SavannaBearerClient()
            # One-time info dialog if expired
            try:
                if getattr(self.savanna_client, 'bearer_token', None):
                    is_expired, _ = self.savanna_client._is_token_expired(self.savanna_client.bearer_token)
                    if is_expired and not self._savanna_token_info_shown:
                        self._savanna_token_info_shown = True
                        self.root.after(300, lambda: messagebox.showinfo(
                            "Savanna Token Expired",
                            "The Savanna Token has expired. Go to Settings to update the token if you want to submit new creatives."
                        ))
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize Savanna client: {e}")
            self.savanna_client = None
        
        # Job monitoring variables
        self.current_run_id = None
        self.monitoring_active = False
        # Advanced window reference for separate window UI
        self.advanced_window = None
        
        # Setup UI
        self.setup_ui()
        
        # Load creatives
        self.load_creatives()
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Apply unified theme
        try:
            from ui.theme import apply_theme as _apply_theme
            _apply_theme(self.root)
        except Exception:
            pass

        # Header row: title only (controls moved to Save section)
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(header_frame, text="Creative Pull App", font=("Arial", 18, "bold"))
        title_label.pack(side=tk.LEFT)
        
        # Create splitter
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Creative list and controls (give more space)
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=3)
        
        # Right panel - Preview area
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        
        self.create_left_panel(left_frame)
        self.create_right_panel(right_frame)
    
    def create_left_panel(self, parent):
        # Simplified left column: Save on top, then Search; Advanced lives under header toggle
        from ui.advanced import create_save_mode_section
        create_save_mode_section(parent, self)
        
        # Main Search Section (Always visible)
        self.create_main_search_section(parent)
        
        # Creative list
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(list_frame, text="Creatives:").pack(anchor=tk.W)
        
        # Create listbox with scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        self.creative_listbox = tk.Listbox(listbox_frame, font=("Courier", 12))
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.creative_listbox.yview)
        self.creative_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.creative_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.creative_listbox.bind('<<ListboxSelect>>', self.on_creative_select)
        self.creative_listbox.bind('<Double-Button-1>', self.on_creative_double_click)
        
        # Status
        self.status_label = ttk.Label(parent, text="Ready", font=("Arial", 11))
        self.status_label.pack(pady=(10, 0))
    
    def create_advanced_features_section(self, parent):
        """Deprecated: Advanced now opens in its own window."""
        pass
    
    def toggle_advanced_features(self):
        """Open/close Advanced as a separate window to avoid taking space."""
        want_open = self.advanced_toggle_var.get()
        try:
            if want_open and (self.advanced_window is None or not self.advanced_window.winfo_exists()):
                win = tk.Toplevel(self.root)
                win.title("Advanced Features")
                win.geometry("640x520")
                self.advanced_window = win
                container = ttk.Frame(win)
                container.pack(fill=tk.BOTH, expand=True)
                from ui.advanced import create_advanced_features_section as _adv
                # Render without inline toggle (window close controls visibility)
                _adv(container, self, show_inline_toggle=False)
                # Ensure container is visible
                self.advanced_features_container.pack(fill=tk.BOTH, expand=True, pady=5)

                def _on_close():
                    try:
                        self.advanced_toggle_var.set(False)
                    except Exception:
                        pass
                    win.destroy()
                win.protocol("WM_DELETE_WINDOW", _on_close)
            elif not want_open and self.advanced_window is not None and self.advanced_window.winfo_exists():
                self.advanced_window.destroy()
        except Exception as e:
            print(f"⚠️ Advanced window error: {e}")
    
    def create_main_search_section(self, parent):
        """Create the main search section (always visible)"""
        # Main Search Frame
        search_frame = ttk.LabelFrame(parent, text="🔍 Creative Search in Persistent DB")
        search_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Search input
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_input_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_input_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.search_entry.bind('<KeyRelease>', self.filter_creatives)
        
        # Refresh DB button
        refresh_button = ttk.Button(search_input_frame, text="🔄 Refresh DB", command=self.refresh_database)
        refresh_button.pack(side=tk.LEFT)
        
        # Search instructions
        instructions_frame = ttk.Frame(search_frame)
        instructions_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        instructions_text = "💡 Tip: Search by Creative ID, Date (MM/DD), Size, or Type"
        instructions_label = ttk.Label(instructions_frame, text=instructions_text, font=("Arial", 9), foreground="gray")
        instructions_label.pack(anchor=tk.W)
    
    # Job runner UI moved to ui.advanced
    
    # Unified Savanna UI moved to ui.advanced
    
    def on_mode_change(self):
        """Handle mode change between search and save"""
        mode = self.savanna_mode_var.get()
        
        def _hide(widget):
            try:
                if widget.winfo_manager() == 'grid':
                    widget.grid_remove()
                else:
                    widget.pack_forget()
            except Exception:
                pass

        def _show(widget):
            try:
                if widget.winfo_manager() == 'grid':
                    widget.grid()
                else:
                    widget.pack(anchor=tk.W, pady=(0, 10))
            except Exception:
                pass

        if mode == "search":
            # Hide Ad Network and Emails
            if hasattr(self, 'ad_network_frame'):
                _hide(self.ad_network_frame)
            if hasattr(self, 'email_frame'):
                _hide(self.email_frame)
            # Update button and info
            self.unified_action_button.config(text="🔍 Search")
            self.info_label.config(text="🔍 Search Mode: Check if a creative exists in the pulling queue")
            # Clear Ad Network ID field
            if hasattr(self, 'unified_ad_network_id_var'):
                self.unified_ad_network_id_var.set("")
        else:  # save mode
            if hasattr(self, 'ad_network_frame'):
                _show(self.ad_network_frame)
            if hasattr(self, 'email_frame'):
                _show(self.email_frame)
            # Update button and info
            self.unified_action_button.config(text="🚀 Submit")
            self.info_label.config(text="💾 Save Mode: Add a new creative to the pulling queue (auto-fills: Creation Date, Expire Date, Active)")
            # Load initial networks for the dropdown
            self._load_initial_networks()
    
    def unified_savanna_action(self):
        """Unified action handler for both search and save modes"""
        mode = self.savanna_mode_var.get()
        
        if mode == "search":
            self.unified_search_creative()
        else:
            self.unified_save_creative()
    
    def unified_search_creative(self):
        """Search for creative in Savanna database"""
        creative_id = self.unified_creative_id_var.get().strip()
        
        if not creative_id:
            messagebox.showwarning("Warning", "Please enter a Creative ID")
            return
        
        # Disable button and show status
        self.unified_action_button.config(state='disabled')
        self.unified_results.config(state=tk.NORMAL)
        self.unified_results.delete(1.0, tk.END)
        self.unified_results.insert(tk.END, f"🔍 Searching for Creative ID: {creative_id}...")
        self.unified_results.config(state=tk.DISABLED)
        self.root.update()
        
        # Search in background thread
        threading.Thread(target=self._unified_search_thread, args=(creative_id,), daemon=True).start()
    
    def unified_save_creative(self):
        """Save one or more creatives to Savanna using a single Demand Source ID."""
        creative_raw = self.unified_creative_id_var.get().strip()
        ad_network_id = self.unified_ad_network_id_var.get().strip()
        user_email = self.unified_email_var.get().strip() if hasattr(self, 'unified_email_var') else ""

        if not creative_raw:
            messagebox.showwarning("Warning", "Please enter at least one Creative ID")
            return

        # Enforce comma-separated IDs. Warn if user used whitespace as delimiter.
        if "," not in creative_raw and re.search(r"\s", creative_raw):
            messagebox.showwarning(
                "Invalid Creative IDs",
                "Separate multiple Creative IDs with commas only (no spaces).\nExample: abc123,def456,ghi789"
            )
            return

        # Split strictly by comma; trim and dedupe (preserve order)
        ids = [c.strip() for c in creative_raw.split(",") if c.strip()]
        # If any token still contains whitespace, warn
        if any(re.search(r"\s", c) for c in ids):
            messagebox.showwarning(
                "Invalid Creative IDs",
                "Creative IDs must not contain spaces. Use commas between IDs with no spaces."
            )
            return
        seen = set()
        creative_ids = []
        for cid in ids:
            if cid not in seen:
                seen.add(cid)
                creative_ids.append(cid)
        if not creative_ids:
            messagebox.showwarning("Warning", "No valid Creative IDs parsed")
            return

        # Limit to at most 10 IDs per submission
        if len(creative_ids) > 10:
            messagebox.showwarning(
                "Too Many Creative IDs",
                f"You can submit up to 10 creatives at a time. You entered {len(creative_ids)}."
            )
            return

        if not ad_network_id:
            messagebox.showwarning("Warning", "Please enter a Demand Source ID")
            return

        # Email validation – enforce comma-separated, no spaces
        if user_email:
            if ";" in user_email:
                messagebox.showwarning("Invalid Emails", "Use commas to separate multiple emails (no semicolons).")
                return
            if re.search(r"\s", user_email):
                messagebox.showwarning("Invalid Emails", "Remove spaces. Separate multiple emails by commas only.")
                return
            parts = [p.strip() for p in user_email.split(",") if p.strip()]
            email_re = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
            invalid = [p for p in parts if email_re.match(p) is None]
            if invalid:
                messagebox.showwarning("Invalid Email(s)", f"These look invalid: {', '.join(invalid)}")
                return

        # Validate ad_network_id is a number
        try:
            int(ad_network_id)
        except ValueError:
            messagebox.showwarning("Warning", "Demand Source ID must be a number")
            return

        # Disable button and show status
        self.unified_action_button.config(state='disabled')
        self.unified_results.config(state=tk.NORMAL)
        self.unified_results.delete(1.0, tk.END)
        self.unified_results.insert(tk.END, f"🚀 Submitting {len(creative_ids)} creative(s) to Savanna using Demand Source ID {ad_network_id}...\n\n")
        self.unified_results.insert(tk.END, "IDs: " + ", ".join(creative_ids[:10]) + ("..." if len(creative_ids) > 10 else "") + "\n")
        self.unified_results.config(state=tk.DISABLED)
        self.root.update()

        # Save in background thread (batch)
        threading.Thread(target=self._unified_save_multi_thread, args=(creative_ids, ad_network_id, user_email), daemon=True).start()
    
    def clear_unified_fields(self):
        """Clear all input fields"""
        self.unified_creative_id_var.set("")
        self.unified_ad_network_id_var.set("")
        self.network_dropdown_var.set("")
        self.unified_results.config(state=tk.NORMAL)
        self.unified_results.delete(1.0, tk.END)
        self.unified_results.insert(tk.END, "🎯 Select a mode and enter Creative ID to get started...")
        self.unified_results.config(state=tk.DISABLED)
        
        # Reload initial networks if in save mode
        if self.savanna_mode_var.get() == "save":
            self._load_initial_networks()
    
    def on_network_search_change(self, event=None):
        """Handle network search input changes with delay to prevent rapid searching"""
        # Cancel any existing timer
        if hasattr(self, '_search_timer'):
            self.root.after_cancel(self._search_timer)
        
        search_term = self.network_dropdown_var.get().strip()
        
        # Don't do anything if user is still typing
        if len(search_term) < 2:
            # Just update status, don't load networks
            self.network_status_label.config(text="Type at least 2 characters to search...")
            return
        
        # Update status
        self.network_status_label.config(text=f"🔍 Searching for networks containing '{search_term}'...")
        
        # Set a timer to search after user stops typing (1000ms delay - increased for better UX)
        self._search_timer = self.root.after(1000, lambda: self._search_networks_thread(search_term))
    
    def _load_initial_networks(self):
        """Load initial list of networks when dropdown is first shown"""
        # Only load if we haven't already loaded networks
        if not self.networks_loaded:
            self.network_status_label.config(text="Loading initial networks...")
            threading.Thread(target=self._search_networks_thread, args=("", True), daemon=True).start()
        else:
            # Networks already loaded, just update status
            self.network_status_label.config(text=f"Loaded {len(self.network_dropdown['values'])} networks")
    
    def _search_networks_thread(self, search_term, is_initial_load=False):
        """Search for networks in background thread"""
        try:
            # Use the existing Savanna client instance
            if not self.savanna_client or not getattr(self.savanna_client, 'bearer_token', None):
                print("❌ Savanna client not available")
                return
            
            from clients.savanna_client import SavannaClientWrapper
            savanna_client = SavannaClientWrapper(self.savanna_client)
            
            # Make API call to search networks - using the exact format from HAR file
            url = "https://savanna.fyber.com/ad-networks"
            
            if is_initial_load:
                # For initial load, get first 25 networks without search filter
                params = {
                    "$limit": "25",
                    "$skip": "0", 
                    "$sort[id]": "-1"
                }
                print(f"🔍 Loading initial networks with params: {params}")
            else:
                # For search, add the name filter
                params = {
                    "$limit": "25",
                    "$skip": "0", 
                    "$sort[id]": "-1",
                    "name[$like]": f"%{search_term}%"
                }
                print(f"🔍 Searching networks with params: {params}")
            
            response = savanna_client.search_networks(url, params, timeout=15)
            
            print(f"📡 API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    networks = data.get('data', [])
                    print(f"📡 Found {len(networks)} networks")
                    
                    if networks:
                        # Extract network names and IDs
                        network_options = []
                        self.network_id_map = {}  # Store mapping of names to IDs
                        
                        for network in networks:
                            name = network.get('name', '')
                            network_id = network.get('id', '')
                            if name and network_id:
                                network_options.append(name)
                                self.network_id_map[name] = network_id
                                print(f"📡 Network: {name} (ID: {network_id})")
                        
                        # Update UI in main thread
                        if is_initial_load:
                            self.root.after(0, lambda: self._network_search_completed(network_options, f"Loaded {len(networks)} networks"))
                        else:
                            self.root.after(0, lambda: self._network_search_completed(network_options, f"Found {len(networks)} networks"))
                    else:
                        self.root.after(0, lambda: self._network_search_completed([], "No networks found"))
                        
                except Exception as json_error:
                    print(f"❌ JSON parsing error: {json_error}")
                    self.root.after(0, lambda: self._network_search_completed([], f"JSON parsing error: {json_error}"))
            elif response.status_code == 401:
                # Inline status next to Submit only; no message under input
                self.root.after(0, lambda: (
                    setattr(self, '_savanna_token_info_shown', True),
                    getattr(self, 'unified_status_label', ttk.Label()).config(text="Unauthorized (token expired)")
                ))
                self.root.after(0, lambda: self._network_search_completed([], ""))
            else:
                error_msg = f"Search failed: {response.status_code}"
                print(f"❌ {error_msg}")
                self.root.after(0, lambda: self._network_search_completed([], error_msg))
                
        except Exception as e:
            error_msg = f"Search error: {str(e)}"
            print(f"❌ {error_msg}")
            self.root.after(0, lambda: self._network_search_completed([], error_msg))
    
    def _network_search_completed(self, network_options, status_message):
        """Handle completed network search"""
        self.network_dropdown['values'] = network_options
        self.network_status_label.config(text=status_message)
        
        if network_options:
            self.network_dropdown.set("")  # Clear selection
            # Mark networks as loaded
            self.networks_loaded = True
        else:
            self.network_dropdown_var.set("")
    
    def on_network_selected(self, event=None):
        """Handle network selection from dropdown"""
        selected_network = self.network_dropdown_var.get()
        
        if selected_network and hasattr(self, 'network_id_map'):
            network_id = self.network_id_map.get(selected_network)
            if network_id:
                # Auto-populate the Ad Network ID field
                self.unified_ad_network_id_var.set(str(network_id))
                self.network_status_label.config(text=f"✅ Selected: {selected_network} (ID: {network_id})")
            else:
                self.network_status_label.config(text="❌ Error: Could not get network ID")
        else:
            self.network_status_label.config(text="Please select a network from the dropdown")
    
    def _unified_search_thread(self, creative_id):
        """Search for creative ID in background thread"""
        try:
            # Use Databricks client via service wrapper
            from clients.databricks_client import DatabricksClient
            from services.savanna_actions import search_creative_in_queue
            client = DatabricksClient()
            results = search_creative_in_queue(
                client,
                DATABRICKS_SERVER_HOSTNAME,
                DATABRICKS_HTTP_PATH,
                self.access_token,
                CREATIVE_PULLING_TABLE,
                creative_id,
            )

            if results:
                # Format results - only essential information
                result_text = f"✅ FOUND: Creative ID '{creative_id}' is in the pulling queue\n\n"
                for i, row in enumerate(results, 1):
                    creative_id, creation_date, expire_date, active = row
                    creation_str = creation_date.strftime('%Y-%m-%d %H:%M:%S') if creation_date else 'N/A'
                    expire_str = expire_date.strftime('%Y-%m-%d %H:%M:%S') if expire_date else 'N/A'
                    result_text += f"📋 Record {i}:\n"
                    result_text += f"   🕒 Created Time: {creation_str}\n"
                    result_text += f"   ⏰ Expire Time: {expire_str}\n"
                    if expire_date:
                        if expire_date.tzinfo is not None:
                            expire_date = expire_date.replace(tzinfo=None)
                        current_time = datetime.now().replace(tzinfo=None)
                        if expire_date < current_time:
                            result_text += f"   ⚠️  Status: EXPIRED\n"
                        elif active:
                            result_text += f"   ✅ Status: ACTIVE\n"
                        else:
                            result_text += f"   ❌ Status: INACTIVE\n"
                    elif active:
                        result_text += f"   ✅ Status: ACTIVE\n"
                    else:
                        result_text += f"   ❌ Status: INACTIVE\n"
                    result_text += "\n"
            else:
                result_text = f"❌ NOT FOUND: Creative ID '{creative_id}' is not in the pulling queue\n\n"
                result_text += "This creative ID has not been added to the pulling queue yet."
            # Update UI in main thread
            self.root.after(0, lambda: self._unified_search_completed(result_text))
                    
        except Exception as e:
            error_msg = f"❌ Error searching for Creative ID: {str(e)}"
            self.root.after(0, lambda: self._unified_search_completed(error_msg))
    
    def _unified_search_completed(self, result_text):
        """Handle completed unified search"""
        self.unified_action_button.config(state='normal')
        self.unified_results.config(state=tk.NORMAL)
        self.unified_results.delete(1.0, tk.END)
        self.unified_results.insert(tk.END, result_text)
        self.unified_results.config(state=tk.DISABLED)
        if hasattr(self, 'unified_status_label'):
            self.unified_status_label.config(text="")
    
    def _unified_save_thread(self, creative_id, ad_network_id, user_email=""):
        """Save creative in background thread"""
        try:
            # Use the existing Savanna client instance
            if not self.savanna_client:
                self.root.after(0, lambda: self._unified_save_completed("❌ Savanna client not available", False))
                return
            
            from services.savanna_actions import build_creation_and_expire_dates, submit_creative
            creation_date, expire_date = build_creation_and_expire_dates()
            result = submit_creative(self.savanna_client, creative_id, int(ad_network_id), creation_date, expire_date, True)
            
            if result:
                success_msg = f"✅ SUCCESS: Creative ID '{creative_id}' submitted to Savanna!\n\n"
                success_msg += f"📋 Details:\n"
                success_msg += f"   🆔 Creative ID: {creative_id}\n"
                success_msg += f"   🌐 Ad Network ID: {ad_network_id}\n"
                success_msg += f"   🕒 Creation Date: {creation_date}\n"
                success_msg += f"   ⏰ Expire Date: {expire_date}\n"
                success_msg += f"   ✅ Active: True\n\n"
                success_msg += f"📡 API Response: {str(result)[:200]}..."
                
                # Insert to watchlist if email(s) provided
                if user_email:
                    try:
                        import re
                        from services.watchlist import insert_watchlist_entries
                        parts = [p.strip() for p in re.split(r"[,;]", user_email) if p.strip()]
                        insert_watchlist_entries(
                            DATABRICKS_SERVER_HOSTNAME,
                            DATABRICKS_HTTP_PATH,
                            self.access_token,
                            creative_id,
                            parts,
                        )
                        success_msg += f"\n📬 Watchlist: queued notification for {', '.join(parts)}"
                    except Exception as e:
                        success_msg += f"\n⚠️ Watchlist insert failed: {e}"
                self.root.after(0, lambda: self._unified_save_completed(success_msg, True))
            else:
                error_msg = f"❌ FAILED: Could not submit Creative ID '{creative_id}' to Savanna"
                self.root.after(0, lambda: self._unified_save_completed(error_msg, False))
                
        except Exception as e:
            error_msg = f"❌ Error submitting creative: {str(e)}"
            self.root.after(0, lambda: self._unified_save_completed(error_msg, False))
    
    def _unified_save_multi_thread(self, creative_ids, ad_network_id, user_email=""):
        """Save multiple creatives in one background task, reusing one Demand Source ID."""
        try:
            if not self.savanna_client:
                self.root.after(0, lambda: self._unified_save_completed("❌ Savanna client not available", False))
                return

            from services.savanna_actions import build_creation_and_expire_dates, submit_creative
            creation_date, expire_date = build_creation_and_expire_dates()

            successes = []
            failures = []

            # Pre-parse email list once
            email_parts = []
            if user_email:
                email_parts = [p.strip() for p in re.split(r"[,;]", user_email) if p.strip()]

            for cid in creative_ids:
                try:
                    result = submit_creative(self.savanna_client, cid, int(ad_network_id), creation_date, expire_date, True)
                    if result:
                        # Watchlist insert per-id if emails provided
                        if email_parts:
                            try:
                                from services.watchlist import insert_watchlist_entries
                                insert_watchlist_entries(
                                    DATABRICKS_SERVER_HOSTNAME,
                                    DATABRICKS_HTTP_PATH,
                                    self.access_token,
                                    cid,
                                    email_parts,
                                )
                                successes.append((cid, True, None))
                            except Exception as e:
                                successes.append((cid, True, f"Watchlist insert failed: {e}"))
                        else:
                            successes.append((cid, True, None))
                    else:
                        failures.append((cid, "Submit returned no result"))
                except Exception as e:
                    failures.append((cid, str(e)))

            # Build aggregate message
            lines = []
            if successes:
                lines.append(f"✅ Submitted {len(successes)} creative(s):")
                for cid, ok, warn in successes[:50]:
                    base = f"  • {cid}"
                    if warn:
                        base += f" (⚠️ {warn})"
                    lines.append(base)
                if len(successes) > 50:
                    lines.append(f"  • …and {len(successes) - 50} more")
            if failures:
                lines.append("")
                lines.append(f"❌ Failed {len(failures)} creative(s):")
                for cid, err in failures[:50]:
                    lines.append(f"  • {cid}: {err}")
                if len(failures) > 50:
                    lines.append(f"  • …and {len(failures) - 50} more")

            result_text = "\n".join(lines) if lines else "No submissions performed."
            overall_success = len(failures) == 0 and len(successes) > 0
            self.root.after(0, lambda: self._unified_save_completed(result_text, overall_success))

        except Exception as e:
            error_msg = f"❌ Error submitting creatives: {str(e)}"
            self.root.after(0, lambda: self._unified_save_completed(error_msg, False))

    def _unified_save_completed(self, result_text, success):
        """Handle completed unified save operation"""
        self.unified_action_button.config(state='normal')
        self.unified_results.config(state=tk.NORMAL)
        self.unified_results.delete(1.0, tk.END)
        self.unified_results.insert(tk.END, result_text)
        self.unified_results.config(state=tk.DISABLED)
        
        # Show popup for success/failure
        if success:
            messagebox.showinfo("Submit Successful", f"Creative submitted successfully!")
        else:
            messagebox.showerror("Submit Failed", f"Failed to submit creative: {result_text}")
        if hasattr(self, 'unified_status_label'):
            self.unified_status_label.config(text="")
    
    def save_creative_to_savanna(self):
        """Save creative to Savanna database"""
        creative_id = self.save_creative_id_var.get().strip()
        ad_network_id = self.save_ad_network_id_var.get().strip()
        
        if not creative_id:
            messagebox.showwarning("Warning", "Please enter a Creative ID")
            return
        
        if not ad_network_id:
            messagebox.showwarning("Warning", "Please enter an Ad Network ID")
            return
        
        # Validate ad_network_id is a number
        try:
            int(ad_network_id)
        except ValueError:
            messagebox.showwarning("Warning", "Ad Network ID must be a number")
            return
        
        # Disable button and show status
        self.save_creative_button.config(state='disabled')
        self.save_creative_results.config(state=tk.NORMAL)
        self.save_creative_results.delete(1.0, tk.END)
        self.save_creative_results.insert(tk.END, f"🚀 Submitting Creative ID: {creative_id} to Savanna...")
        self.save_creative_results.config(state=tk.DISABLED)
        self.root.update()
        
        # Save in background thread
        threading.Thread(target=self._save_creative_thread, args=(creative_id, ad_network_id), daemon=True).start()
    
    def _save_creative_thread(self, creative_id, ad_network_id):
        """Save creative in background thread"""
        try:
            # Use the existing Savanna client instance
            if not self.savanna_client:
                self.save_creative_results.config(state=tk.NORMAL)
                self.save_creative_results.delete(1.0, tk.END)
                self.save_creative_results.insert(tk.END, "❌ Savanna client not available")
                self.save_creative_results.config(state=tk.DISABLED)
                self.save_creative_button.config(state='normal')
                return
            
            from services.savanna_actions import build_creation_and_expire_dates, submit_creative
            creation_date, expire_date = build_creation_and_expire_dates()
            result = submit_creative(self.savanna_client, creative_id, int(ad_network_id), creation_date, expire_date, True)
            
            if result:
                success_msg = f"✅ SUCCESS: Creative ID '{creative_id}' submitted to Savanna!\n\n"
                success_msg += f"📋 Details:\n"
                success_msg += f"   🆔 Creative ID: {creative_id}\n"
                success_msg += f"   🌐 Ad Network ID: {ad_network_id}\n"
                success_msg += f"   🕒 Creation Date: {creation_date}\n"
                success_msg += f"   ⏰ Expire Date: {expire_date}\n"
                success_msg += f"   ✅ Active: True\n\n"
                success_msg += f"📡 API Response: {str(result)[:200]}..."
                
                self.root.after(0, lambda: self._save_completed(success_msg, True))
            else:
                error_msg = f"❌ FAILED: Could not submit Creative ID '{creative_id}' to Savanna"
                self.root.after(0, lambda: self._save_completed(error_msg, False))
                
        except Exception as e:
            error_msg = f"❌ Error submitting creative: {str(e)}"
            self.root.after(0, lambda: self._save_completed(error_msg, False))
    
    def _save_completed(self, result_text, success):
        """Handle completed save operation"""
        self.save_creative_button.config(state='normal')
        self.save_creative_results.config(state=tk.NORMAL)
        self.save_creative_results.delete(1.0, tk.END)
        self.save_creative_results.insert(tk.END, result_text)
        self.save_creative_results.config(state=tk.DISABLED)
        
        # Show popup for success/failure
        if success:
            messagebox.showinfo("Submit Successful", f"Creative submitted successfully!")
        else:
            messagebox.showerror("Submit Failed", f"Failed to submit creative: {result_text}")
        
    def _build_iso_ts_from_date_hour(self, date_str: str, hour_str: str) -> str:
        """Build ISO8601 UTC timestamp (truncated to hour) from date 'YYYY-MM-DD' and hour 'HH'."""
        try:
            base = datetime.strptime(date_str, '%Y-%m-%d')
            hour = int(hour_str)
            dt = base.replace(hour=hour, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            return dt.isoformat().replace('+00:00', 'Z')
        except Exception:
            return ""

    def set_last_6_hours(self):
        """Quick fill last 6 whole hours [now-6h, now)."""
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        start = now - timedelta(hours=6)
        if hasattr(self, 'start_date_var') and hasattr(self, 'start_hour_var') and hasattr(self, 'end_date_var') and hasattr(self, 'end_hour_var'):
            self.start_date_var.set(start.strftime('%Y-%m-%d'))
            self.start_hour_var.set(start.strftime('%H'))
            self.end_date_var.set(now.strftime('%Y-%m-%d'))
            self.end_hour_var.set(now.strftime('%H'))

    def set_today_hours(self):
        """Quick fill for today from 00:00Z to current hour."""
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if hasattr(self, 'start_date_var') and hasattr(self, 'start_hour_var') and hasattr(self, 'end_date_var') and hasattr(self, 'end_hour_var'):
            self.start_date_var.set(now.strftime('%Y-%m-%d'))
            self.start_hour_var.set('00')
            self.end_date_var.set(now.strftime('%Y-%m-%d'))
            self.end_hour_var.set(now.strftime('%H'))

    def set_yesterday_hours(self):
        """Quick fill for yesterday full day [00:00Z, 24:00Z)."""
        today0 = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        yday0 = today0 - timedelta(days=1)
        if hasattr(self, 'start_date_var') and hasattr(self, 'start_hour_var') and hasattr(self, 'end_date_var') and hasattr(self, 'end_hour_var'):
            self.start_date_var.set(yday0.strftime('%Y-%m-%d'))
            self.start_hour_var.set('00')
            self.end_date_var.set(today0.strftime('%Y-%m-%d'))
            self.end_hour_var.set('00')
    
    def run_job(self):
        """Run the Databricks job using Start/End date+hour fields as ISO UTC."""
        try:
            # Build ISO timestamps
            start_ts = ""
            end_ts = ""
            if hasattr(self, 'start_date_var') and hasattr(self, 'start_hour_var'):
                start_ts = self._build_iso_ts_from_date_hour(self.start_date_var.get().strip(), self.start_hour_var.get().strip())
            if hasattr(self, 'end_date_var') and hasattr(self, 'end_hour_var'):
                end_ts = self._build_iso_ts_from_date_hour(self.end_date_var.get().strip(), self.end_hour_var.get().strip())

            # Validate window: both provided and <= 3 days
            if start_ts and end_ts:
                try:
                    sdt = datetime.strptime(start_ts.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S%z')
                    edt = datetime.strptime(end_ts.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S%z')
                    if edt <= sdt:
                        messagebox.showerror("Error", "End Time must be after Start Time")
                        return
                    if (edt - sdt) > timedelta(days=3):
                        messagebox.showerror("Error", "Time window too large. Please select 3 days or less.")
                        return
                except Exception:
                    # If parsing fails, continue and let backend validate
                    pass

            params = {}
            if start_ts:
                params["start_ts"] = start_ts
            if end_ts:
                params["end_ts"] = end_ts
            
            # Disable button and show status
            self.run_job_button.config(state='disabled')
            self.job_status_label.config(text="🔄 Running job...")
            self.root.update()
            
            # Run job in background thread
            threading.Thread(target=self._run_job_thread, args=(params,), daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start job: {str(e)}")
            self.run_job_button.config(state='normal')
            self.job_status_label.config(text="❌ Job failed to start")
    
    def _run_job_thread(self, params):
        """Run the job in a background thread"""
        try:
            # Update UI with initial status
            self.root.after(0, lambda: self._update_job_status("🚀 Preparing to start job..."))
            
            # Use Databricks client
            from clients.databricks_client import DatabricksClient
            client = DatabricksClient()
            self.root.after(0, lambda: self._update_job_status("📡 Sending job request to Databricks..."))
            # Updated client should accept a params dict; fallback to day-mode signature if present
            try:
                response = client.run_job_with_params(DATABRICKS_WORKSPACE_URL, self.access_token, JOB_ID, params)
            except Exception:
                # Back-compat: if only day-mode available
                response = client.run_job(DATABRICKS_WORKSPACE_URL, self.access_token, JOB_ID, params.get('start_date',''), params.get('end_date',''))
            
            if response.status_code == 200:
                result = response.json()
                run_id = result.get('run_id')
                
                # Update UI with success
                self.root.after(0, lambda: self._update_job_status(f"✅ Job started successfully!\n🆔 Run ID: {run_id}"))
                
                # Start monitoring the job
                self.root.after(0, lambda: self._start_job_monitoring(run_id))
            else:
                error_msg = f"Failed to start job: {response.status_code} - {response.text}"
                self.root.after(0, lambda: self._job_failed(error_msg))
                
        except Exception as e:
            error_msg = f"Error running job: {str(e)}"
            self.root.after(0, lambda: self._job_failed(error_msg))
    
    def _start_job_monitoring(self, run_id):
        """Start monitoring the job progress"""
        self.current_run_id = run_id
        self.monitoring_active = True
        # Spinner setup
        self._spinner_frames = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
        self._spinner_idx = 0
        self._base_job_status_text = self.job_status_label.cget("text")
        self._spinner_job = None
        self._tick_spinner()
        self.root.after(0, lambda: self._monitor_job_progress(run_id))
    
    def _monitor_job_progress(self, run_id):
        """Monitor job progress and update UI"""
        if not self.monitoring_active:
            return
            
        try:
            # Use Databricks client
            from clients.databricks_client import DatabricksClient
            client = DatabricksClient()
            response = client.get_run_status(DATABRICKS_WORKSPACE_URL, self.access_token, run_id)
            
            if response.status_code == 200:
                result = response.json()
                state = result.get('state', {})
                life_cycle_state = state.get('life_cycle_state', 'UNKNOWN')
                result_state = state.get('result_state', 'UNKNOWN')
                state_message = state.get('state_message', '')
                
                # Format timestamps
                start_time = result.get('start_time', 0)
                end_time = result.get('end_time', 0)
                
                start_str = "N/A"
                if start_time:
                    start_dt = datetime.fromtimestamp(start_time / 1000)
                    start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                end_str = "N/A"
                if end_time:
                    end_dt = datetime.fromtimestamp(end_time / 1000)
                    end_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Create status message
                status_parts = [
                    f"🆔 Run ID: {run_id}",
                    f"🏃‍♂️ Status: {life_cycle_state}",
                    f"📊 Result: {result_state}",
                    f"🕐 Started: {start_str}"
                ]
                
                if end_time:
                    status_parts.append(f"🕐 Ended: {end_str}")
                
                if state_message:
                    status_parts.append(f"💬 Message: {state_message}")
                
                # Add task information if available
                if 'tasks' in result:
                    tasks = result['tasks']
                    if tasks:
                        task = tasks[0]  # Usually one task per job
                        task_state = task.get('state', {})
                        task_life_cycle = task_state.get('life_cycle_state', 'UNKNOWN')
                        task_result = task_state.get('result_state', 'UNKNOWN')
                        status_parts.append(f"🔧 Task Status: {task_life_cycle} / {task_result}")
                
                status_text = "\n".join(status_parts)
                
                # Update UI and base text for spinner overlay
                self._base_job_status_text = status_text
                self.root.after(0, lambda: self._update_job_status(self._compose_spinner_text()))
                
                # Check if job is complete
                if life_cycle_state in ['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR']:
                    self.monitoring_active = False
                    self._stop_spinner()
                    if result_state == 'SUCCESS':
                        self.root.after(0, lambda: self._job_completed_successfully(run_id))
                    else:
                        self.root.after(0, lambda: self._job_completed_with_error(run_id, result_state, state_message))
                else:
                    # Continue monitoring - check again in 10 seconds
                    self.root.after(10000, lambda: self._monitor_job_progress(run_id))
            else:
                error_msg = f"Failed to check job status: {response.status_code} - {response.text}"
                self.root.after(0, lambda: self._job_failed(error_msg))
                self.monitoring_active = False
                self._stop_spinner()
                
        except Exception as e:
            error_msg = f"Error monitoring job: {str(e)}"
            self.root.after(0, lambda: self._job_failed(error_msg))
            self.monitoring_active = False
    
    def _update_job_status(self, status_text):
        """Update the job status label"""
        self.job_status_label.config(text=status_text)
        self.root.update()

    def _compose_spinner_text(self):
        try:
            frame = self._spinner_frames[self._spinner_idx % len(self._spinner_frames)]
        except Exception:
            frame = '⏳'
        return f"{self._base_job_status_text}\n{frame} Updating..."

    def _tick_spinner(self):
        if not getattr(self, 'monitoring_active', False):
            return
        self._spinner_idx = (getattr(self, '_spinner_idx', 0) + 1) % 1000000
        self.job_status_label.config(text=self._compose_spinner_text())
        self._spinner_job = self.root.after(400, self._tick_spinner)

    def _stop_spinner(self):
        try:
            if getattr(self, '_spinner_job', None) is not None:
                self.root.after_cancel(self._spinner_job)
                self._spinner_job = None
        except Exception:
            pass
    
    def _job_completed_successfully(self, run_id):
        """Handle successful job completion"""
        self.run_job_button.config(state='normal')
        self.monitoring_active = False
        self.job_status_label.config(text=f"✅ Job completed successfully!\n🆔 Run ID: {run_id}")
        messagebox.showinfo("Job Completed", f"Job completed successfully!\nRun ID: {run_id}")
    
    def _job_completed_with_error(self, run_id, result_state, state_message):
        """Handle job completion with error"""
        self.run_job_button.config(state='normal')
        self.monitoring_active = False
        error_text = f"❌ Job completed with error!\n🆔 Run ID: {run_id}\n📊 Result: {result_state}"
        if state_message:
            error_text += f"\n💬 Error: {state_message}"
        self.job_status_label.config(text=error_text)
        messagebox.showerror("Job Failed", error_text)
    
    def _job_failed(self, error_msg):
        """Handle job failure"""
        self.run_job_button.config(state='normal')
        self.monitoring_active = False
        self.job_status_label.config(text="❌ Job failed")
        messagebox.showerror("Job Failed", error_msg)
    
    def check_job_status(self):
        """Check the status of the most recent job run"""
        try:
            # Disable button and show status
            self.check_job_status_button.config(state='disabled')
            self.job_status_label.config(text="🔄 Checking job status...")
            self.root.update()
            
            # Check status in background thread
            threading.Thread(target=self._check_job_status_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check job status: {str(e)}")
            self.check_job_status_button.config(state='normal')
            self.job_status_label.config(text="❌ Status check failed")
    
    def _check_job_status_thread(self):
        """Check job status in background thread"""
        try:
            # Use Databricks client
            from clients.databricks_client import DatabricksClient
            client = DatabricksClient()
            response = client.list_recent_runs(DATABRICKS_WORKSPACE_URL, self.access_token, JOB_ID, limit=5)
            
            if response.status_code == 200:
                job_runs = response.json()
                runs = job_runs.get('runs', [])
                
                if runs:
                    latest_run = runs[0]  # Most recent run
                    run_id = latest_run.get('run_id')
                    state = latest_run.get('state', {})
                    life_cycle_state = state.get('life_cycle_state', 'UNKNOWN')
                    result_state = state.get('result_state', 'UNKNOWN')
                    start_time = latest_run.get('start_time', 0)
                    end_time = latest_run.get('end_time', 0)
                    
                    # Format timestamps
                    start_str = 'N/A'
                    if start_time:
                        start_dt = datetime.fromtimestamp(start_time / 1000)
                        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    end_str = 'N/A'
                    if end_time:
                        end_dt = datetime.fromtimestamp(end_time / 1000)
                        end_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Create user-friendly status message
                    status_parts = [f"🆔 Run ID: {run_id}"]
                    
                    # Show user-friendly status based on result_state
                    if result_state == 'SUCCESS':
                        status_parts.append("✅ Status: Completed Successfully")
                    elif result_state == 'FAILED':
                        status_parts.append("❌ Status: Failed")
                    elif result_state == 'CANCELLED':
                        status_parts.append("⚠️ Status: Cancelled")
                    elif result_state == 'TIMEDOUT':
                        status_parts.append("⏰ Status: Timed Out")
                    else:
                        # For running or unknown states, show lifecycle state
                        if life_cycle_state == 'RUNNING':
                            status_parts.append("🔄 Status: Running")
                        elif life_cycle_state == 'PENDING':
                            status_parts.append("⏳ Status: Pending")
                        elif life_cycle_state == 'TERMINATED':
                            status_parts.append("✅ Status: Completed")
                        else:
                            status_parts.append(f"❓ Status: {life_cycle_state}")
                    
                    status_parts.append(f"🕐 Started: {start_str}")
                    
                    if end_time:
                        status_parts.append(f"🕐 Ended: {end_str}")
                    
                    # Add duration if both times are available
                    if start_time and end_time:
                        duration_seconds = (end_time - start_time) / 1000
                        if duration_seconds < 60:
                            duration_str = f"{duration_seconds:.1f}s"
                        elif duration_seconds < 3600:
                            duration_str = f"{duration_seconds/60:.1f}m"
                        else:
                            duration_str = f"{duration_seconds/3600:.1f}h"
                        status_parts.append(f"⏱️ Duration: {duration_str}")
                    
                    status_text = "\n".join(status_parts)
                    
                    self.root.after(0, lambda: self._status_check_completed(status_text))
                else:
                    self.root.after(0, lambda: self._status_check_completed("No runs found for this job"))
            else:
                error_msg = f"Failed to check status: {response.status_code} - {response.text}"
                self.root.after(0, lambda: self._status_check_failed(error_msg))
                
        except Exception as e:
            error_msg = f"Error checking status: {str(e)}"
            self.root.after(0, lambda: self._status_check_failed(error_msg))
    
    def _status_check_completed(self, status_text):
        """Handle completed status check"""
        self.check_job_status_button.config(state='normal')
        self.job_status_label.config(text=status_text)
        
        # Don't show popup by default - status is already displayed in the UI
        # Only show popup for errors or if specifically requested
    
    def _status_check_failed(self, error_msg):
        """Handle failed status check"""
        self.check_job_status_button.config(state='normal')
        self.job_status_label.config(text="❌ Status check failed")
        messagebox.showerror("Status Check Failed", error_msg)
    
    def create_right_panel(self, parent):
        # Title
        title_label = ttk.Label(parent, text="🎬 Preview Area", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.preview_button = ttk.Button(button_frame, text="🎬 Preview in Browser", command=self.show_preview)
        self.preview_button.pack(side=tk.LEFT)
        
        # External helper: test-a-tag.com
        def open_test_a_tag():
            try:
                webbrowser.open_new_tab("https://test-a-tag.com/")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open test-a-tag.com: {e}")
        self.test_a_tag_button = ttk.Button(button_frame, text="🔗 test-a-tag.com", command=open_test_a_tag)
        self.test_a_tag_button.pack(side=tk.LEFT, padx=(8, 0))
        
        # Info frame
        info_frame = ttk.LabelFrame(parent, text="Creative Info")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=6, font=("Courier", 12))
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Markup frame
        markup_frame = ttk.LabelFrame(parent, text="Raw Markup")
        markup_frame.pack(fill=tk.BOTH, expand=True)
        
        # Small buttons next to markup label
        markup_button_frame = ttk.Frame(markup_frame)
        markup_button_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        self.copy_markup_small_button = ttk.Button(markup_button_frame, text="📋 Copy", command=self.copy_markup, width=8)
        self.copy_markup_small_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.beautify_small_button = ttk.Button(markup_button_frame, text="🔧 Beautify", command=self.format_xml, width=8)
        self.beautify_small_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.download_markup_button = ttk.Button(markup_button_frame, text="💾 Download", command=self.download_markup, width=12)
        self.download_markup_button.pack(side=tk.LEFT)
        
        self.markup_text = scrolledtext.ScrolledText(markup_frame, font=("Courier", 11))
        self.markup_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def load_creatives(self):
        """Load creatives from Databricks in a separate thread"""
        def load_thread():
            try:
                self.status_label.config(text="Loading creatives from Databricks...")
                
                from clients.databricks_client import DatabricksClient
                client = DatabricksClient()
                creatives = client.get_latest_creatives(
                    DATABRICKS_SERVER_HOSTNAME,
                    DATABRICKS_HTTP_PATH,
                    self.access_token,
                    DATABRICKS_TABLE_NAME,
                )
                # Update UI in main thread
                self.root.after(0, self.on_data_loaded, creatives)
                        
            except Exception as e:
                error_msg = f"Error loading creatives: {str(e)}"
                print(f"❌ {error_msg}")
                self.root.after(0, self.on_error, error_msg)
        
        # Start loading thread
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def on_data_loaded(self, creatives):
        """Handle loaded creatives data"""
        self.creatives = creatives
        self.update_creative_list()
        self.status_label.config(text=f"✅ Loaded {len(creatives)} creatives")
        print(f"✅ SUCCESS: Loaded {len(creatives)} creatives from Databricks")
    
    def on_error(self, error_msg):
        """Handle loading error"""
        self.status_label.config(text=f"❌ Error: {error_msg}")
        
        # Check if it's a token error and offer to retry with new token
        if "Invalid access token" in error_msg or "access token" in error_msg.lower():
            retry = messagebox.askyesno(
                "Invalid Token", 
                f"Databricks connection failed: {error_msg}\n\n" +
                "This usually means your access token is expired or invalid.\n\n" +
                "Would you like to enter a new token?"
            )
            
            if retry:
                new_token = self.prompt_for_token()
                if new_token:
                    self.access_token = new_token
                    print("🔄 Retrying with new token...")
                    self.load_creatives()
                    return
        
        messagebox.showerror("Error", error_msg)
    
    def update_creative_list(self):
        """Update the creative listbox"""
        self.creative_listbox.delete(0, tk.END)
        for creative in self.creatives:
            # Format the date nicely - handle different date types
            try:
                if creative['day']:
                    if hasattr(creative['day'], 'strftime'):
                        # It's a datetime object
                        day_str = creative['day'].strftime('%m/%d')
                    else:
                        # It's a string or other type
                        day_str = str(creative['day'])[:10]  # Take first 10 chars for date
                else:
                    day_str = 'N/A'
            except Exception as e:
                day_str = 'N/A'
                print(f"⚠️ Date formatting error: {e}")
            
            display_text = f"{day_str} | {creative['id']} | {creative['size']} | {creative['type']}"
            self.creative_listbox.insert(tk.END, display_text)
    
    def filter_creatives(self, *args):
        """Filter creatives based on search term"""
        search_term = self.search_var.get().lower()
        self.creative_listbox.delete(0, tk.END)
        
        for creative in self.creatives:
            # Format the date nicely - handle different date types
            try:
                if creative['day']:
                    if hasattr(creative['day'], 'strftime'):
                        # It's a datetime object
                        day_str = creative['day'].strftime('%m/%d')
                    else:
                        # It's a string or other type
                        day_str = str(creative['day'])[:10]
                else:
                    day_str = 'N/A'
            except Exception as e:
                day_str = 'N/A'
            
            if (search_term in str(creative['id']).lower() or 
                search_term in creative['size'].lower() or 
                search_term in str(creative['type']).lower() or
                search_term in day_str.lower()):
                display_text = f"{day_str} | {creative['id']} | {creative['size']} | {creative['type']}"
                self.creative_listbox.insert(tk.END, display_text)
    
    def refresh_database(self):
        """Refresh the database and reload creatives"""
        try:
            print("🔄 Refreshing database...")
            
            # Update status
            if hasattr(self, 'job_status_label'):
                self.job_status_label.config(text="🔄 Refreshing database...")
            
            # Reload creatives from Databricks
            self.load_creatives()
            
            # Update status
            if hasattr(self, 'job_status_label'):
                self.job_status_label.config(text="✅ Database refreshed successfully!")
            
            print("✅ Database refresh completed")
            
        except Exception as e:
            error_msg = f"Failed to refresh database: {str(e)}"
            print(f"❌ {error_msg}")
            
            if hasattr(self, 'job_status_label'):
                self.job_status_label.config(text=f"❌ Refresh failed: {str(e)}")
            
            messagebox.showerror("Refresh Error", error_msg)
    
    def on_creative_select(self, event):
        """Handle creative selection"""
        selection = self.creative_listbox.curselection()
        if selection:
            index = selection[0]
            # Find the creative in the filtered list
            search_term = self.search_var.get().lower()
            filtered_creatives = []
            
            for c in self.creatives:
                # Format the date for search
                try:
                    if c['day']:
                        if hasattr(c['day'], 'strftime'):
                            day_str = c['day'].strftime('%m/%d')
                        else:
                            day_str = str(c['day'])[:10]
                    else:
                        day_str = 'N/A'
                except Exception:
                    day_str = 'N/A'
                
                if (search_term in str(c['id']).lower() or 
                    search_term in c['size'].lower() or 
                    search_term in str(c['type']).lower() or
                    search_term in day_str.lower()):
                    filtered_creatives.append(c)
            
            if index < len(filtered_creatives):
                self.selected_creative = filtered_creatives[index]
                self.display_creative()
    
    def on_creative_double_click(self, event):
        """Handle creative double-click - show preview"""
        self.on_creative_select(event)
        if self.selected_creative:
            self.show_preview()
    
    def display_creative(self):
        """Display the selected creative"""
        if not self.selected_creative:
            return
        
        print("🎨 Displaying creative...")
        print(f"📄 Creative ID: {self.selected_creative['id']}")
        print(f"📅 Date: {self.selected_creative['day']}")
        print(f"📏 Size: {self.selected_creative['size']}")
        print(f"🎬 Type: {self.selected_creative['type']}")
        print(f"📝 Markup length: {len(self.selected_creative['markup']) if self.selected_creative['markup'] else 0}")
        
        # Parse the markup
        parsed_result = self.parse_ad_response(self.selected_creative['markup'])
        
        if parsed_result.get('error'):
            print(f"❌ Failed to parse creative: {parsed_result['error']}")
            self.current_markup = ""
            self.current_type = "unknown"
        else:
            self.current_markup = parsed_result.get('creative', '')
            self.current_type = parsed_result.get('type', 'display')
            print(f"✅ Parsed creative type: {self.current_type}")
            print(f"✅ Parsed markup length: {len(self.current_markup)}")
        
        # Update info display
        info_text = f"""Creative ID: {self.selected_creative['id']}
Size: {self.selected_creative['size']}
Type: {self.selected_creative['type']}
Parsed Type: {self.current_type}
Markup Length: {len(self.current_markup)} characters

Raw Type: {self.selected_creative['type']}
Raw Size: {self.selected_creative['size']}"""
        
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info_text)
        
        # Update markup display
        self.markup_text.delete(1.0, tk.END)
        if self.current_markup:
            self.markup_text.insert(1.0, self.current_markup)
    
    def parse_ad_response(self, xml_string):
        """Delegate XML parsing to a stateless helper for clarity."""
        from utils.markup_parser import parse_ad_response as _parse
        return _parse(xml_string)
    
    def decode_html_entities(self, text):
        from ui.preview import decode_html_entities as _decode
        return _decode(text)
    
    def extract_vast_url(self, markup):
        """Proxy to utils.vast_utils.extract_vast_url for maintainability."""
        return util_extract_vast_url(markup)
    
    def _process_vast_chain(self, vast_url, wrapper_count=0):
        """Process VAST chain recursively like the React app - follows wrappers to find InLine"""
        MAX_VAST_WRAPPERS = 5
        
        if wrapper_count > MAX_VAST_WRAPPERS:
            raise Exception('Exceeded maximum VAST wrapper redirects')
        
        print(f"🔄 Processing VAST Chain - Level {wrapper_count}")
        
        try:
            # Fetch VAST XML
            response = requests.get(vast_url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch VAST XML: {response.status_code}")
            
            vast_xml = response.text
            print(f"📄 Fetched VAST XML: {len(vast_xml)} chars")
            
            # Parse XML
            try:
                root = ET.fromstring(vast_xml)
            except ET.ParseError as e:
                raise Exception(f"Invalid XML: {e}")
            
            # Check for InLine (final ad)
            inline_ad = root.find('.//InLine')
            if inline_ad is not None:
                print("✅ Found InLine VAST. Extracting video URL...")
                
                # Find Linear creative
                linear = inline_ad.find('.//Linear')
                if linear is None:
                    raise Exception('InLine VAST does not contain a Linear creative')
                
                # Find MediaFile with video/mp4 or .mp4 extension
                media_files = []
                for media_file in linear.findall('.//MediaFile'):
                    url = media_file.text.strip() if media_file.text else ''
                    media_type = media_file.get('type', '')
                    
                    if media_type == 'video/mp4' or url.endswith('.mp4'):
                        bitrate = int(media_file.get('bitrate', '0') or '0')
                        media_files.append({
                            'url': url,
                            'type': media_type,
                            'bitrate': bitrate
                        })
                
                if not media_files:
                    raise Exception('No MP4 MediaFile found in InLine VAST')
                
                # Sort by bitrate (highest first) like the React app
                media_files.sort(key=lambda x: x['bitrate'], reverse=True)
                primary_video = media_files[0]
                
                print(f"🎬 Found video URL: {primary_video['url']}")
                return primary_video['url']
            
            # Check for Wrapper (needs to fetch another VAST)
            wrapper_ad = root.find('.//Wrapper')
            if wrapper_ad is not None:
                print(f"🔄 Found Wrapper {wrapper_count + 1}. Getting VASTAdTagURI...")
                
                vast_ad_tag_uri = wrapper_ad.find('.//VASTAdTagURI')
                if vast_ad_tag_uri is None or not vast_ad_tag_uri.text:
                    raise Exception('Wrapper VAST does not contain a VASTAdTagURI')
                
                next_vast_url = vast_ad_tag_uri.text.strip()
                print(f"🔄 Following URI: {next_vast_url}")
                
                # Recursively process the next VAST
                return self._process_vast_chain(next_vast_url, wrapper_count + 1)
            
            # Neither InLine nor Wrapper found
            raise Exception('VAST XML contains neither InLine nor Wrapper Ad element')
            
        except Exception as e:
            print(f"❌ Error during VAST processing (Level {wrapper_count}): {e}")
            raise
    
    def extract_vast_click_through(self, markup):
        """Proxy to utils.vast_utils.extract_vast_click_through."""
        return util_extract_vast_click(markup)

    def _get_inline_vast_xml_from_markup(self, markup):
        """Delegate to utils.vast_utils.get_inline_vast_xml_from_markup."""
        return util_get_inline_vast_xml(markup)

    # _fetch_inline_vast_xml now provided by utils; kept only via _get_inline_vast_xml_from_markup
    
    # _extract_click_through_from_vast_chain now handled in utils via extract_vast_click_through
    
    def show_preview(self):
        """Show preview in webview window"""
        if not self.current_markup:
            messagebox.showwarning("Warning", "No creative selected!")
            return
        
        if self.current_type == 'vast':
            self.show_vast_preview()
        else:
            self.show_display_preview()
    
    def show_display_preview(self):
        """Show display ad preview in webview"""
        if not self.current_markup:
            messagebox.showwarning("Warning", "No markup to preview!")
            return
        from ui.preview import build_display_preview_html, save_html_to_temp_and_open
        html_content = build_display_preview_html(self.selected_creative, self.current_type, self.current_markup)
        save_html_to_temp_and_open(html_content, label='display')
    
    def show_vast_preview(self):
        """Show VAST video preview in webview"""
        if not self.current_markup:
            messagebox.showwarning("Warning", "No VAST markup to preview!")
            return
        
        # Extract VAST URL and click-through
        vast_url = self.extract_vast_url(self.current_markup)
        click_through_url = self.extract_vast_click_through(self.current_markup)
        
        if not vast_url:
            messagebox.showwarning("Warning", "No VAST URL found!")
            return
        
        # Create HTML content for VAST preview via helper
        from ui.preview import (
            build_vast_preview_html,
            extract_companion_ad_info,
            is_portrait_video_from_size,
            save_html_to_temp_and_open,
        )
        # Extract companions by combining wrapper and inner InLine VAST
        inline_vast_xml = self._get_inline_vast_xml_from_markup(self.current_markup)
        if inline_vast_xml:
            companion_info = extract_companion_ad_info(inline_vast_xml)
            if not companion_info.get('found'):
                # Fallback to wrapper markup too
                wrapper_try = extract_companion_ad_info(self.current_markup)
                if wrapper_try.get('found'):
                    companion_info = wrapper_try
        else:
            companion_info = extract_companion_ad_info(self.current_markup)
        is_portrait = is_portrait_video_from_size(self.selected_creative['size'] if self.selected_creative else None)
        html_content = build_vast_preview_html(
            selected_creative=self.selected_creative,
            current_type=self.current_type,
            vast_url=vast_url,
            click_through_url=click_through_url,
            is_portrait=is_portrait,
            companion_info_html=companion_info['html'] if companion_info.get('found') else None,
        )
        print(f"🎬 Video URL: {vast_url}")
        save_html_to_temp_and_open(html_content, label='VAST')
    
    def _extract_companion_ad_info(self, markup):
        from ui.preview import extract_companion_ad_info
        return extract_companion_ad_info(markup)
    
    def _is_portrait_video(self):
        """Check if the video is portrait orientation"""
        if not self.selected_creative:
            return False
        
        size = self.selected_creative['size']
        if 'x' in size:
            try:
                width, height = size.split('x')
                w, h = int(width), int(height)
                # Portrait if height > width OR if it's a mobile-style video (like 480x320)
                return h > w or (w <= 480 and h <= 640)
            except ValueError:
                return False
        return False
    
    def copy_markup(self):
        """Copy markup to clipboard"""
        if self.current_markup:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_markup)
        else:
            messagebox.showwarning("Warning", "No markup to copy!")
    
    def download_markup(self):
        """Download markup to a local text file"""
        if not self.current_markup:
            messagebox.showwarning("Warning", "No markup to download!")
            return
        
        try:
            from tkinter import filedialog
            import os
            from datetime import datetime
            import re
            
            # Prefer creative ID as the default filename (sanitized), fallback to timestamped name
            creative_id = None
            try:
                if hasattr(self, 'selected_creative') and self.selected_creative is not None:
                    creative_id = str(self.selected_creative.get('id') or '').strip()
            except Exception:
                creative_id = None

            # Sanitize for cross-platform filenames
            safe_id = None
            if creative_id:
                safe_id = re.sub(r"[^A-Za-z0-9._-]+", "_", creative_id)
                if not safe_id:
                    safe_id = None

            if safe_id:
                default_filename = f"{safe_id}.txt"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_filename = f"creative_markup_{timestamp}.txt"
            
            # Open file dialog for save location
            file_path = filedialog.asksaveasfilename(
                title="Save Creative Markup",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=default_filename
            )
            
            if file_path:
                # Write markup to file
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.current_markup)
                
                # Show success message
                messagebox.showinfo(
                    "Success", 
                    f"Markup saved successfully!\n\nFile: {os.path.basename(file_path)}\nLocation: {os.path.dirname(file_path)}"
                )
                
                print(f"✅ Markup downloaded to: {file_path}")
                
        except Exception as e:
            error_msg = f"Failed to download markup: {str(e)}"
            messagebox.showerror("Error", error_msg)
            print(f"❌ {error_msg}")
    
    def show_settings(self):
        # Delegate to modular settings UI
        from ui.settings import show_settings as _show
        _show(self)

    # Settings helpers moved to ui.settings

    # Settings UI moved to ui.settings

    # Databricks settings UI moved to ui.settings
    
    def format_xml(self):
        """Format XML markup in the text area"""
        if not self.current_markup:
            messagebox.showwarning("Warning", "No markup to format!")
            return
        
        try:
            import xml.etree.ElementTree as ET
            import re
            
            # Clean up the markup first (remove CDATA if present)
            clean_markup = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', self.current_markup)
            
            # Try to parse as XML
            try:
                root = ET.fromstring(clean_markup)
                formatted_xml = self._format_xml_element(root, 0)
            except ET.ParseError:
                # If XML parsing fails, use simple formatting
                formatted_xml = self._simple_format_xml(self.current_markup)
            
            # Update the markup text area
            self.markup_text.delete(1.0, tk.END)
            self.markup_text.insert(1.0, formatted_xml)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to format XML: {str(e)}")
    
    def _format_xml_element(self, element, indent_level):
        from ui.preview import format_xml_element
        return format_xml_element(element, indent_level)
    
    def _simple_format_xml(self, xml_string):
        from ui.preview import simple_format_xml
        return simple_format_xml(xml_string)


        
    # Configuration helpers are now in config.app_config
    
    def extract_token_from_har(self, har_file_path: str) -> str:
        from utils.har_utils import extract_token_from_har as _extract
        return _extract(har_file_path)
    
    def save_token_to_config(self, token):
        from config.app_config import save_token_to_config as _save
        _save(token)
    
    def show_token_help(self):
        """Show helpful message about how to provide token"""
        help_message = """
Databricks Token Required

The Creative Pull App needs a Databricks Personal Access Token to connect to the database.

🔐 How to get your token:
1. Go to: https://3218046436603353.3.gcp.databricks.com
2. Click your profile (top right) → User Settings
3. Go to "Access Tokens" tab
4. Click "Generate New Token"
5. Set name: "Creative Pull App"
6. Set expiration: 90 days (or as allowed)
7. Copy the token (starts with 'dapi')

💾 How to provide the token:

Option 1 (Recommended for sharing):
Set environment variable:
• macOS/Linux: export DATABRICKS_ACCESS_TOKEN="your_token_here"
• Windows: set DATABRICKS_ACCESS_TOKEN=your_token_here

Option 2 (Local development):
Create config.ini file with:
[DATABRICKS]
access_token = your_token_here

Option 3 (Interactive):
The app will prompt you to enter the token when you run it.

🔒 Security Notes:
• Never share your personal token with others
• Each user should generate their own token
• Tokens expire and need to be renewed periodically
        """
        
        messagebox.showinfo("Token Help", help_message)

def main():
    root = tk.Tk()
    app = CreativePreviewerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
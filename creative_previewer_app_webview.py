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
from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
# import webview  # Removed due to threading issues on macOS
from databricks import sql
import xml.etree.ElementTree as ET
import configparser

import html
import re
import requests

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
        self.access_token = self.load_configuration()
        
        # Job monitoring variables
        self.current_run_id = None
        self.monitoring_active = False
        
        # Setup UI
        self.setup_ui()
        
        # Load creatives (this will validate the token)
        self.load_creatives()
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create splitter
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Creative list and controls
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # Right panel - Preview area
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        
        self.create_left_panel(left_frame)
        self.create_right_panel(right_frame)
    
    def create_left_panel(self, parent):
        # Title
        title_label = ttk.Label(parent, text="Creative Pull App", font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Advanced Features Section (Collapsible)
        self.create_advanced_features_section(parent)
        
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
        """Create collapsible advanced features section"""
        # Advanced Features Frame
        advanced_frame = ttk.LabelFrame(parent, text="⚙️ Advanced Features")
        advanced_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Toggle button for advanced features
        self.advanced_toggle_var = tk.BooleanVar(value=False)
        self.advanced_toggle_button = ttk.Checkbutton(
            advanced_frame, 
            text="Show Advanced Features", 
            variable=self.advanced_toggle_var,
            command=self.toggle_advanced_features
        )
        self.advanced_toggle_button.pack(pady=5)
        
        # Container for advanced features (initially hidden)
        self.advanced_features_container = ttk.Frame(advanced_frame)
        
        # Job Runner Section
        self.create_job_runner_section(self.advanced_features_container)
        
        # Creative ID Search Section
        self.create_creative_search_section(self.advanced_features_container)
    
    def toggle_advanced_features(self):
        """Toggle the visibility of advanced features"""
        if self.advanced_toggle_var.get():
            self.advanced_features_container.pack(fill=tk.X, pady=5)
        else:
            self.advanced_features_container.pack_forget()
    
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
        self.search_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.search_entry.bind('<KeyRelease>', self.filter_creatives)
        
        # Search instructions
        instructions_frame = ttk.Frame(search_frame)
        instructions_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        instructions_text = "💡 Tip: Search by Creative ID, Date (MM/DD), Size, or Type"
        instructions_label = ttk.Label(instructions_frame, text=instructions_text, font=("Arial", 9), foreground="gray")
        instructions_label.pack(anchor=tk.W)
    
    def create_job_runner_section(self, parent):
        """Create the job runner section with date range selection"""
        # Job Runner Frame
        job_frame = ttk.LabelFrame(parent, text="🚀 Job Runner")
        job_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Date Range Selection
        date_frame = ttk.Frame(job_frame)
        date_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Start Date
        start_date_frame = ttk.Frame(date_frame)
        start_date_frame.pack(fill=tk.X, pady=2)
        ttk.Label(start_date_frame, text="Start Date (GMT):").pack(side=tk.LEFT)
        
        # Get current date in GMT
        current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        self.start_date_var = tk.StringVar(value=current_date)
        self.start_date_entry = ttk.Entry(start_date_frame, textvariable=self.start_date_var, width=12)
        self.start_date_entry.pack(side=tk.RIGHT)
        
        # End Date
        end_date_frame = ttk.Frame(date_frame)
        end_date_frame.pack(fill=tk.X, pady=2)
        ttk.Label(end_date_frame, text="End Date (GMT):").pack(side=tk.LEFT)
        
        self.end_date_var = tk.StringVar(value=current_date)
        self.end_date_entry = ttk.Entry(end_date_frame, textvariable=self.end_date_var, width=12)
        self.end_date_entry.pack(side=tk.RIGHT)
        
        # Quick date buttons
        quick_date_frame = ttk.Frame(job_frame)
        quick_date_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(quick_date_frame, text="Today", command=self.set_today, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_date_frame, text="Yesterday", command=self.set_yesterday, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_date_frame, text="Last 3 Days", command=self.set_last_3_days, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_date_frame, text="Last 7 Days", command=self.set_last_7_days, width=10).pack(side=tk.LEFT, padx=2)
        
        # Job Control Buttons
        button_frame = ttk.Frame(job_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.run_job_button = ttk.Button(button_frame, text="▶️ Run Job", command=self.run_job, style="Accent.TButton")
        self.run_job_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.check_job_status_button = ttk.Button(button_frame, text="📊 Check Status", command=self.check_job_status)
        self.check_job_status_button.pack(side=tk.LEFT, padx=2)
        
        # Job Status Display - Made larger for better visibility
        status_frame = ttk.Frame(job_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.job_status_label = ttk.Label(status_frame, text="Ready to run job", font=("Arial", 10), wraplength=400, justify=tk.LEFT)
        self.job_status_label.pack(fill=tk.X, pady=(5, 0))
    
    def create_creative_search_section(self, parent):
        """Create the creative ID search section"""
        # Creative Search Frame
        search_frame = ttk.LabelFrame(parent, text="🔍 Creative Submitted in Savanna")
        search_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Creative ID Input
        id_frame = ttk.Frame(search_frame)
        id_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(id_frame, text="Creative ID:").pack(side=tk.LEFT)
        self.creative_id_var = tk.StringVar()
        self.creative_id_entry = ttk.Entry(id_frame, textvariable=self.creative_id_var, width=25)
        self.creative_id_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        self.search_creative_button = ttk.Button(id_frame, text="🔍 Search", command=self.search_creative_id)
        self.search_creative_button.pack(side=tk.LEFT, padx=2)
        
        # Results Display - Made bigger
        results_frame = ttk.Frame(search_frame)
        results_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.creative_search_results = scrolledtext.ScrolledText(results_frame, height=6, font=("Arial", 12))
        self.creative_search_results.pack(fill=tk.BOTH, expand=True)
        self.creative_search_results.insert(tk.END, "Enter a Creative ID and click Search to check if it's in the pulling queue...")
        self.creative_search_results.config(state=tk.DISABLED)
    
    def set_today(self):
        """Set both start and end date to today"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        self.start_date_var.set(today)
        self.end_date_var.set(today)
    
    def set_yesterday(self):
        """Set both start and end date to yesterday"""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
        self.start_date_var.set(yesterday)
        self.end_date_var.set(yesterday)
    
    def set_last_3_days(self):
        """Set date range to last 3 days"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=2)
        self.start_date_var.set(start_date.strftime('%Y-%m-%d'))
        self.end_date_var.set(end_date.strftime('%Y-%m-%d'))
    
    def set_last_7_days(self):
        """Set date range to last 7 days"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=6)
        self.start_date_var.set(start_date.strftime('%Y-%m-%d'))
        self.end_date_var.set(end_date.strftime('%Y-%m-%d'))
    
    def run_job(self):
        """Run the Databricks job with the selected date range"""
        try:
            # Validate dates
            start_date = self.start_date_var.get()
            end_date = self.end_date_var.get()
            
            if not start_date or not end_date:
                messagebox.showerror("Error", "Please enter both start and end dates")
                return
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Error", "Please enter dates in YYYY-MM-DD format")
                return
            
            # Disable button and show status
            self.run_job_button.config(state='disabled')
            self.job_status_label.config(text="🔄 Running job...")
            self.root.update()
            
            # Run job in background thread
            threading.Thread(target=self._run_job_thread, args=(start_date, end_date), daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start job: {str(e)}")
            self.run_job_button.config(state='normal')
            self.job_status_label.config(text="❌ Job failed to start")
    
    def _run_job_thread(self, start_date, end_date):
        """Run the job in a background thread"""
        try:
            # Update UI with initial status
            self.root.after(0, lambda: self._update_job_status("🚀 Preparing to start job..."))
            
            # Prepare job parameters
            job_params = {
                "job_id": JOB_ID,
                "notebook_params": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            }
            
            # API endpoint
            api_url = f"{DATABRICKS_WORKSPACE_URL}/api/2.1/jobs/run-now"
            
            # Headers
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Update UI
            self.root.after(0, lambda: self._update_job_status("📡 Sending job request to Databricks..."))
            
            # Make the API request
            response = requests.post(api_url, headers=headers, json=job_params, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                run_id = result.get('run_id')
                
                # Update UI with success
                self.root.after(0, lambda: self._update_job_status(f"✅ Job started successfully!\n🆔 Run ID: {run_id}\n📅 Date Range: {start_date} to {end_date}"))
                
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
        self.root.after(0, lambda: self._monitor_job_progress(run_id))
    
    def _monitor_job_progress(self, run_id):
        """Monitor job progress and update UI"""
        if not self.monitoring_active:
            return
            
        try:
            # Get job run status
            api_url = f"{DATABRICKS_WORKSPACE_URL}/api/2.1/jobs/runs/get"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            params = {"run_id": run_id}
            
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            
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
                
                # Update UI
                self.root.after(0, lambda: self._update_job_status(status_text))
                
                # Check if job is complete
                if life_cycle_state in ['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR']:
                    self.monitoring_active = False
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
                
        except Exception as e:
            error_msg = f"Error monitoring job: {str(e)}"
            self.root.after(0, lambda: self._job_failed(error_msg))
            self.monitoring_active = False
    
    def _update_job_status(self, status_text):
        """Update the job status label"""
        self.job_status_label.config(text=status_text)
        self.root.update()
    
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
            # Get recent runs
            api_url = f"{DATABRICKS_WORKSPACE_URL}/api/2.1/jobs/runs/list"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "limit": 5,
                "offset": 0,
                "job_id": JOB_ID
            }
            
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            
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
        title_label = ttk.Label(parent, text="Preview Area", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.preview_button = ttk.Button(button_frame, text="🎬 Preview in Browser", command=self.show_preview)
        self.preview_button.pack(side=tk.LEFT)
        
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
        self.beautify_small_button.pack(side=tk.LEFT)
        
        self.markup_text = scrolledtext.ScrolledText(markup_frame, font=("Courier", 11))
        self.markup_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def load_creatives(self):
        """Load creatives from Databricks in a separate thread"""
        def load_thread():
            try:
                self.status_label.config(text="Loading creatives from Databricks...")
                
                # Databricks connection
                connection_params = {
                    "server_hostname": DATABRICKS_SERVER_HOSTNAME,
                    "http_path": DATABRICKS_HTTP_PATH,
                    "access_token": self.access_token
                }
                
                with sql.connect(**connection_params) as connection:
                    with connection.cursor() as cursor:
                        # Query to get creatives with day column
                        query = f"""
                        SELECT day, creativeId, adSize, type, markup 
                        FROM {DATABRICKS_TABLE_NAME} 
                        ORDER BY day DESC
                        LIMIT 500
                        """
                        
                        cursor.execute(query)
                        results = cursor.fetchall()
                        
                        # Process results
                        creatives = []
                        for row in results:
                            day, creative_id, ad_size, ad_type, markup = row
                            
                            # Parse ad_size to get width and height
                            size_parts = ad_size.split('x') if ad_size else ['0', '0']
                            width = size_parts[0] if len(size_parts) > 0 else '0'
                            height = size_parts[1] if len(size_parts) > 1 else '0'
                            
                            creative = {
                                'day': day,
                                'id': creative_id,
                                'size': ad_size,
                                'width': width,
                                'height': height,
                                'type': ad_type,
                                'markup': markup
                            }
                            creatives.append(creative)
                        
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
        """Parse ad response XML - same logic as React app"""
        if not xml_string:
            return {'error': 'No XML content provided'}
        
        print(f"🔍 Parsing XML string of length: {len(xml_string)}")
        print(f"📄 First 200 chars: {xml_string[:200]}...")
        
        try:
            # Parse XML
            root = ET.fromstring(xml_string)
            
            # Extract dimensions and type
            width = None
            height = None
            ad_type = None
            
            # Look for namespace-aware elements
            TNS_NAMESPACE_URI = "http://www.inner-active.com/SimpleM2M/M2MResponse"
            
            # Try to find elements with namespace
            width_elem = root.find(f'.//{{{TNS_NAMESPACE_URI}}}AdWidth')
            height_elem = root.find(f'.//{{{TNS_NAMESPACE_URI}}}AdHeight')
            type_elem = root.find(f'.//{{{TNS_NAMESPACE_URI}}}AdType')
            
            if width_elem is not None:
                width = width_elem.get('Value')
            if height_elem is not None:
                height = height_elem.get('Value')
            if type_elem is not None:
                ad_type = type_elem.get('Value')
            
            print(f"📏 Width: {width}, Height: {height}, Type: {ad_type}")
            
            # Find Ad element
            ad_elem = root.find(f'.//{{{TNS_NAMESPACE_URI}}}Ad')
            if ad_elem is None:
                ad_elem = root.find('.//Ad')  # Fallback without namespace
            
            if ad_elem is None:
                return {'error': 'No Ad element found'}
            
            print("✅ Found Ad element")
            
            # Extract CDATA content
            cdata_content = None
            print("🔍 Looking for CDATA content...")
            
            # Look for CDATA sections
            for child in ad_elem:
                if child.tag is ET.Comment:
                    continue
                if child.text and child.text.strip():
                    cdata_content = child.text.strip()
                    break
            
            # Fallback to text content
            if not cdata_content:
                cdata_content = ad_elem.text.strip() if ad_elem.text else ""
                print(f"📝 Using text content: {len(cdata_content)} chars")
            
            if not cdata_content:
                return {'error': 'No CDATA content found'}
            
            # Process based on AdType
            if ad_type == '4':  # Display Ad
                print("✅ Processed as display ad")
                creative = self.decode_html_entities(cdata_content)
                return {
                    'type': 'display',
                    'creative': creative,
                    'width': width,
                    'height': height
                }
            elif ad_type == '8':  # VAST Ad
                print("✅ Processed as VAST ad")
                creative = self.decode_html_entities(cdata_content)
                return {
                    'type': 'vast',
                    'creative': creative,
                    'width': width,
                    'height': height
                }
            else:
                # Unknown type - try to determine from content
                print(f"🎯 Final result - Type: display, Creative length: {len(cdata_content)}")
                creative = self.decode_html_entities(cdata_content)
                return {
                    'type': 'display',
                    'creative': creative,
                    'width': width,
                    'height': height
                }
                
        except ET.ParseError as e:
            return {'error': f'XML parsing error: {str(e)}'}
        except Exception as e:
            return {'error': f'Unexpected error: {str(e)}'}
    
    def decode_html_entities(self, text):
        """Decode HTML entities"""
        if not text:
            return text
        
        # Use html.unescape for basic entities
        decoded = html.unescape(text)
        
        # Additional replacements for common entities
        replacements = {
            '&nbsp;': ' ',
            '&#39;': "'",
            '&#34;': '"',
            '&#60;': '<',
            '&#62;': '>',
            '&#38;': '&',
            '&#160;': ' '
        }
        
        for entity, replacement in replacements.items():
            decoded = decoded.replace(entity, replacement)
        
        return decoded
    
    def extract_vast_url(self, markup):
        """Extract VAST URL from markup - following the React app approach"""
        import re
        import html
        from xml.etree import ElementTree as ET
        
        # First, look for VASTAdTagURI (this is the VAST XML endpoint for wrapper VAST)
        vast_ad_tag_patterns = [
            r'<VASTAdTagURI><!\[CDATA\[(.*?)\]\]></VASTAdTagURI>',
            r'<VASTAdTagURI>(.*?)</VASTAdTagURI>'
        ]
        
        for pattern in vast_ad_tag_patterns:
            match = re.search(pattern, markup, re.IGNORECASE)
            if match:
                vast_xml_url = match.group(1)
                # Decode HTML entities in the URL
                vast_xml_url = html.unescape(vast_xml_url)
                print(f"🎯 Found VAST XML URL (wrapper): {vast_xml_url}")
                
                # Follow the VAST chain like the React app does
                try:
                    return self._process_vast_chain(vast_xml_url)
                except Exception as e:
                    print(f"❌ Error processing VAST chain: {e}")
                    return vast_xml_url  # Fallback to original URL
        
        # If no VASTAdTagURI found, this might be a direct VAST response
        print("🔍 No VASTAdTagURI found, checking for direct MediaFile...")
        
        # Try to parse the markup as XML to find MediaFile
        try:
            # Clean up the markup first (remove CDATA if present)
            clean_markup = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', markup)
            
            # Parse as XML
            root = ET.fromstring(clean_markup)
            
            # Look for MediaFile elements
            media_files = []
            for media_file in root.findall('.//MediaFile'):
                url = media_file.text.strip() if media_file.text else ''
                media_type = media_file.get('type', '')
                
                if media_type == 'video/mp4' or url.endswith('.mp4'):
                    bitrate = int(media_file.get('bitrate', '0') or '0')
                    media_files.append({
                        'url': url,
                        'type': media_type,
                        'bitrate': bitrate
                    })
            
            if media_files:
                # Sort by bitrate (highest first) like the React app
                media_files.sort(key=lambda x: x['bitrate'], reverse=True)
                primary_video = media_files[0]
                print(f"🎬 Found direct MediaFile URL: {primary_video['url']}")
                return primary_video['url']
                
        except ET.ParseError as e:
            print(f"❌ Error parsing markup as XML: {e}")
        
        # Fallback: look for direct MediaFile URLs using regex
        direct_media_patterns = [
            r'<MediaFile[^>]*><!\[CDATA\[(.*?)\]\]></MediaFile>',
            r'<MediaFile[^>]*>(.*?)</MediaFile>',
            r'<URL><!\[CDATA\[(.*?)\]\]></URL>',
            r'<URL>(.*?)</URL>'
        ]
        
        for pattern in direct_media_patterns:
            match = re.search(pattern, markup, re.IGNORECASE)
            if match:
                media_url = match.group(1).strip()
                if media_url and (media_url.endswith('.mp4') or 'video' in media_url):
                    print(f"🎬 Found direct MediaFile URL (regex): {media_url}")
                    return media_url
        
        print("❌ No VAST URL found in markup")
        return None
    
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
        """Extract click-through URL from VAST markup - following the React app approach"""
        # First, look for VASTAdTagURI to get the VAST XML
        vast_ad_tag_patterns = [
            r'<VASTAdTagURI><!\[CDATA\[(.*?)\]\]></VASTAdTagURI>',
            r'<VASTAdTagURI>(.*?)</VASTAdTagURI>'
        ]
        
        for pattern in vast_ad_tag_patterns:
            match = re.search(pattern, markup, re.IGNORECASE)
            if match:
                vast_xml_url = match.group(1)
                # Decode HTML entities in the URL
                vast_xml_url = html.unescape(vast_xml_url)
                print(f"🎯 Looking for click-through in VAST: {vast_xml_url}")
                
                # Follow the VAST chain to find click-through
                try:
                    return self._extract_click_through_from_vast_chain(vast_xml_url)
                except Exception as e:
                    print(f"❌ Error extracting click-through from VAST chain: {e}")
                    break
        
        # Fallback: look for direct click-through URLs in the original markup
        click_patterns = [
            r'<ClickThrough><!\[CDATA\[(.*?)\]\]></ClickThrough>',
            r'<ClickThrough>(.*?)</ClickThrough>',
            r'<ClickTracking><!\[CDATA\[(.*?)\]\]></ClickTracking>',
            r'<ClickTracking>(.*?)</ClickTracking>'
        ]
        
        for pattern in click_patterns:
            match = re.search(pattern, markup, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_click_through_from_vast_chain(self, vast_url, wrapper_count=0):
        """Extract click-through URL from VAST chain recursively"""
        MAX_VAST_WRAPPERS = 5
        
        if wrapper_count > MAX_VAST_WRAPPERS:
            raise Exception('Exceeded maximum VAST wrapper redirects')
        
        try:
            # Fetch VAST XML
            response = requests.get(vast_url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch VAST XML: {response.status_code}")
            
            vast_xml = response.text
            
            # Parse XML
            try:
                root = ET.fromstring(vast_xml)
            except ET.ParseError as e:
                raise Exception(f"Invalid XML: {e}")
            
            # Check for InLine (final ad)
            inline_ad = root.find('.//InLine')
            if inline_ad is not None:
                print("✅ Found InLine VAST. Extracting click-through...")
                
                # Find Linear creative
                linear = inline_ad.find('.//Linear')
                if linear is None:
                    raise Exception('InLine VAST does not contain a Linear creative')
                
                # Find VideoClicks and ClickThrough
                video_clicks = linear.find('.//VideoClicks')
                if video_clicks is not None:
                    click_through = video_clicks.find('.//ClickThrough')
                    if click_through is not None and click_through.text:
                        click_url = click_through.text.strip()
                        print(f"🔗 Found click-through URL: {click_url}")
                        return click_url
                
                return None
            
            # Check for Wrapper (needs to fetch another VAST)
            wrapper_ad = root.find('.//Wrapper')
            if wrapper_ad is not None:
                print(f"🔄 Found Wrapper {wrapper_count + 1}. Following for click-through...")
                
                vast_ad_tag_uri = wrapper_ad.find('.//VASTAdTagURI')
                if vast_ad_tag_uri is None or not vast_ad_tag_uri.text:
                    raise Exception('Wrapper VAST does not contain a VASTAdTagURI')
                
                next_vast_url = vast_ad_tag_uri.text.strip()
                
                # Recursively process the next VAST
                return self._extract_click_through_from_vast_chain(next_vast_url, wrapper_count + 1)
            
            # Neither InLine nor Wrapper found
            raise Exception('VAST XML contains neither InLine nor Wrapper Ad element')
            
        except Exception as e:
            print(f"❌ Error during click-through extraction (Level {wrapper_count}): {e}")
            raise
    
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
        
        # Create HTML content
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Display Ad Preview</title>
            <style>
                body {{ 
                    margin: 0; 
                    padding: 20px; 
                    font-family: Arial, sans-serif; 
                    background: #f5f5f5;
                }}
                .ad-container {{ 
                    border: 2px solid #ddd; 
                    border-radius: 8px;
                    padding: 20px; 
                    background: white;
                    max-width: 100%;
                    overflow: auto;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .ad-content {{ 
                    max-width: 480px;
                    max-height: 320px;
                    margin: 0 auto;
                    overflow: auto;
                }}
                .preview-header {{
                    background: #007bff;
                    color: white;
                    padding: 10px 20px;
                    margin: -20px -20px 20px -20px;
                    border-radius: 6px 6px 0 0;
                    font-weight: bold;
                    font-size: 16px;
                }}
                .info-panel {{
                    background: #e9ecef;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 10px;
                    margin: 10px 0;
                    font-size: 12px;
                    color: #495057;
                }}
            </style>
        </head>
        <body>
            <div class="ad-container">
                <div class="preview-header">
                    🎨 Display Ad Preview - {self.selected_creative['size'] if self.selected_creative else 'Unknown'}
                </div>
                <div class="info-panel">
                    <strong>Creative Info:</strong> ID: {self.selected_creative['id'] if self.selected_creative else 'Unknown'}, 
                    Size: {self.selected_creative['size'] if self.selected_creative else 'Unknown'}, Type: {self.current_type}
                </div>
                <div class="ad-content">
                    {self.current_markup}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save to temporary file with better error handling
        import tempfile
        import os
        
        try:
            # Create temporary file in system temp directory
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_file = f.name
            
            print(f"📄 Created display preview file: {temp_file}")
            print(f"📄 File size: {os.path.getsize(temp_file)} bytes")
            
            # Open in external browser
            file_url = f"file://{os.path.abspath(temp_file)}"
            print(f"🌐 Opening URL: {file_url}")
            webbrowser.open(file_url)
            
        except Exception as e:
            print(f"❌ Error creating display preview: {e}")
            messagebox.showerror("Error", f"Could not create display preview: {e}")
    
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
        
        # Create HTML content for VAST preview
        # Extract companion ad info
        companion_info = self._extract_companion_ad_info(self.current_markup)
        
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VAST Video Preview</title>
            <style>
                body {{ 
                    margin: 0; 
                    padding: 20px; 
                    font-family: Arial, sans-serif; 
                    background: #f5f5f5;
                    font-size: 14px;
                }}
                .vast-container {{ 
                    border: 2px solid #ddd; 
                    border-radius: 8px;
                    padding: 30px; 
                    background: white;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    max-width: 95vw;
                    width: 100%;
                    margin: 0 auto;
                    box-sizing: border-box;
                }}
                .vast-player {{
                    max-width: 100%;
                    margin: 20px auto;
                    text-align: center;
                }}
                .video-container {{
                    width: 100%;
                    max-width: 100%;
                    margin: 0 auto;
                    overflow: hidden;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    position: relative;
                }}
                .video-container video {{
                    width: 100%;
                    height: auto;
                    object-fit: contain;
                    display: block;
                }}
                .video-container.portrait {{
                    max-width: 400px;
                    margin: 20px auto;
                }}
                .video-container.portrait video {{
                    max-width: 400px;
                    max-height: 600px;
                    width: auto;
                    height: auto;
                }}
                .video-container.landscape {{
                    max-width: 100%;
                    margin: 20px auto;
                    aspect-ratio: 16/9;
                }}
                .video-container.landscape video {{
                    width: 100%;
                    height: 100%;
                    max-height: 70vh;
                    object-fit: contain;
                }}
                /* Responsive design for different screen sizes */
                @media (min-width: 1200px) {{
                    .video-container.landscape {{
                        max-width: 1000px;
                        aspect-ratio: 16/9;
                    }}
                }}
                @media (min-width: 768px) and (max-width: 1199px) {{
                    .video-container.landscape {{
                        max-width: 90vw;
                        aspect-ratio: 16/9;
                    }}
                }}
                @media (max-width: 767px) {{
                    .video-container.landscape {{
                        max-width: 95vw;
                        aspect-ratio: 16/9;
                    }}
                    .video-container.portrait {{
                        max-width: 300px;
                    }}
                }}
                .url-section {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin: 20px 0;
                }}
                .vast-url {{
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 15px;
                    font-family: monospace;
                    word-break: break-all;
                    text-align: left;
                    font-size: 11px;
                    position: relative;
                    min-height: 80px;
                }}
                .vast-url.single {{
                    grid-column: 1 / -1;
                }}
                @media (max-width: 768px) {{
                    .url-section {{
                        grid-template-columns: 1fr;
                    }}
                }}
                .copy-button {{
                    position: absolute;
                    top: 5px;
                    right: 5px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 2px 8px;
                    font-size: 10px;
                    cursor: pointer;
                }}
                .copy-button:hover {{
                    background: #0056b3;
                }}
                .preview-header {{
                    background: #28a745;
                    color: white;
                    padding: 15px 25px;
                    margin: -30px -30px 25px -30px;
                    border-radius: 6px 6px 0 0;
                    font-weight: bold;
                    font-size: 18px;
                }}
                .info-panel {{
                    background: #e9ecef;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 15px;
                    margin: 15px 0;
                    font-size: 14px;
                    color: #495057;
                }}
                .companion-section {{
                    margin-top: 20px;
                    border-top: 2px solid #dee2e6;
                    padding-top: 20px;
                }}
                .companion-ad {{
                    border: 1px solid #ccc;
                    margin: 10px auto;
                    max-width: 300px;
                    background: white;
                }}
                .button-row {{
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                    margin: 15px 0;
                    flex-wrap: wrap;
                }}
                .action-button {{
                    background: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 12px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                }}
                .action-button:hover {{
                    background: #545b62;
                }}
                .action-button.primary {{
                    background: #007bff;
                }}
                .action-button.primary:hover {{
                    background: #0056b3;
                }}
            </style>
            <script>
                function copyToClipboard(text) {{
                    navigator.clipboard.writeText(text).then(function() {{
                        // Show a brief "Copied!" message
                        const button = event.target;
                        const originalText = button.textContent;
                        button.textContent = 'Copied!';
                        button.style.background = '#28a745';
                        setTimeout(function() {{
                            button.textContent = originalText;
                            button.style.background = '#007bff';
                        }}, 1000);
                    }});
                }}
                
                // Responsive video sizing
                function resizeVideo() {{
                    const videoContainer = document.querySelector('.video-container.landscape');
                    const video = videoContainer ? videoContainer.querySelector('video') : null;
                    
                    if (video && videoContainer) {{
                        const containerWidth = videoContainer.offsetWidth;
                        const aspectRatio = 16/9;
                        const calculatedHeight = containerWidth / aspectRatio;
                        
                        // Set max height to 70% of viewport height
                        const maxHeight = window.innerHeight * 0.7;
                        const finalHeight = Math.min(calculatedHeight, maxHeight);
                        
                        videoContainer.style.height = finalHeight + 'px';
                        video.style.height = '100%';
                        video.style.width = '100%';
                    }}
                }}
                
                // Initialize and handle window resize
                window.addEventListener('load', resizeVideo);
                window.addEventListener('resize', resizeVideo);
                
                // Also resize when video loads
                document.addEventListener('DOMContentLoaded', function() {{
                    const video = document.querySelector('video');
                    if (video) {{
                        video.addEventListener('loadedmetadata', resizeVideo);
                    }}
                }});
            </script>
        </head>
        <body>
            <div class="vast-container">
                <div class="preview-header">
                    🎬 VAST Video Ad Player - {self.selected_creative['size'] if self.selected_creative else 'Unknown'}
                </div>
                <div class="info-panel">
                    <strong>Creative Info:</strong> ID: {self.selected_creative['id'] if self.selected_creative else 'Unknown'}, 
                    Size: {self.selected_creative['size'] if self.selected_creative else 'Unknown'}, Type: {self.current_type}
                </div>
                

                
                <div class="vast-player">
                    <div class="video-container{' portrait' if self._is_portrait_video() else ' landscape'}">
                        <video controls>
                            <source src="{vast_url}" type="video/mp4">
                            <source src="{vast_url}" type="video/webm">
                            <source src="{vast_url}" type="video/ogg">
                            Your browser does not support the video tag.
                        </video>
                    </div>
                </div>
                
                <div class="url-section">
                    <div class="vast-url{' single' if not click_through_url else ''}">
                        <button class="copy-button" onclick="copyToClipboard('{vast_url}')">Copy</button>
                        <strong>🎯 Video URL:</strong><br>
                        {vast_url}
                    </div>
                    
                    {f'<div class="vast-url"><button class="copy-button" onclick="copyToClipboard(\'{click_through_url}\')">Copy</button><strong>🔗 Click-Through URL:</strong><br>{click_through_url}</div>' if click_through_url else ''}
                </div>
                
                {companion_info['html'] if companion_info['found'] else '<div class="companion-section"><h3>🖼️ Companion Ads</h3><p>No Companion</p></div>'}
            </div>
        </body>
        </html>
        """
        
        # Save to temporary file with better error handling
        import tempfile
        import os
        
        try:
            # Create temporary file in system temp directory
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_file = f.name
            
            print(f"📄 Created VAST preview file: {temp_file}")
            print(f"📄 File size: {os.path.getsize(temp_file)} bytes")
            print(f"🎬 Video URL: {vast_url}")
            
            # Open in external browser
            file_url = f"file://{os.path.abspath(temp_file)}"
            print(f"🌐 Opening URL: {file_url}")
            webbrowser.open(file_url)
            
        except Exception as e:
            print(f"❌ Error creating VAST preview: {e}")
            messagebox.showerror("Error", f"Could not create VAST preview: {e}")
    
    def _extract_companion_ad_info(self, markup):
        """Extract companion ad information from VAST markup"""
        import re
        from xml.etree import ElementTree as ET
        
        try:
            # Clean up the markup first (remove CDATA if present)
            clean_markup = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', markup)
            
            # Parse as XML
            root = ET.fromstring(clean_markup)
            
            # Look for CompanionAds
            companion_ads = root.findall('.//Companion')
            
            if not companion_ads:
                return {'found': False, 'html': ''}
            
            companion_html = """
            <div class="companion-section">
                <h3>🖼️ Companion Ads</h3>
            """
            
            for i, companion in enumerate(companion_ads):
                companion_id = companion.get('id', f'companion_{i}')
                width = companion.get('width', 'Unknown')
                height = companion.get('height', 'Unknown')
                
                # Find StaticResource (image)
                static_resource = companion.find('.//StaticResource')
                image_url = static_resource.text.strip() if static_resource is not None and static_resource.text else None
                
                # Find CompanionClickThrough
                click_through = companion.find('.//CompanionClickThrough')
                click_url = click_through.text.strip() if click_through is not None and click_through.text else None
                
                companion_html += f"""
                <div class="companion-ad">
                    <div style="padding: 10px; border-bottom: 1px solid #dee2e6;">
                        <strong>Companion Ad {i+1}</strong> (ID: {companion_id})<br>
                        Size: {width}x{height}
                    </div>
                """
                
                if image_url:
                    companion_html += f"""
                    <div style="padding: 10px;">
                        <img src="{image_url}" style="max-width: 100%; height: auto; border: 1px solid #ddd;" alt="Companion Ad">
                        <div class="vast-url" style="margin-top: 10px;">
                            <button class="copy-button" onclick="copyToClipboard('{image_url}')">Copy</button>
                            <strong>🖼️ Image URL:</strong><br>
                            {image_url}
                        </div>
                    </div>
                    """
                
                if click_url:
                    companion_html += f"""
                    <div class="vast-url" style="margin: 10px;">
                        <button class="copy-button" onclick="copyToClipboard('{click_url}')">Copy</button>
                        <strong>🔗 Click URL:</strong><br>
                        {click_url}
                    </div>
                    """
                
                companion_html += "</div>"
            
            companion_html += "</div>"
            
            return {'found': True, 'html': companion_html}
            
        except ET.ParseError as e:
            print(f"❌ Error parsing VAST for companion ads: {e}")
            return {'found': False, 'html': ''}
        except Exception as e:
            print(f"❌ Error extracting companion ad info: {e}")
            return {'found': False, 'html': ''}
    
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
        """Recursively format XML element with proper indentation"""
        spaces = "    " * indent_level
        result = ""
        
        # Start tag with attributes
        result += spaces + "<" + element.tag
        
        # Add attributes
        for key, value in element.attrib.items():
            result += f' {key}="{value}"'
        
        # Check if element has children
        children = list(element)
        text_content = element.text.strip() if element.text else ""
        
        if children or (text_content and len(children) > 0):
            # Element has children or mixed content
            result += ">\n"
            
            # Add text content if present
            if text_content:
                result += spaces + "    " + text_content + "\n"
            
            # Add child elements
            for child in children:
                result += self._format_xml_element(child, indent_level + 1) + "\n"
            
            result += spaces + "</" + element.tag + ">"
        elif text_content:
            # Element has only text content
            result += ">" + text_content + "</" + element.tag + ">"
        else:
            # Self-closing element
            result += "/>"
        
        return result
    
    def _simple_format_xml(self, xml_string):
        """Simple XML formatting fallback"""
        # Clean up CDATA sections first
        xml_string = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', xml_string)
        
        # Add line breaks after tags
        xml_string = xml_string.replace('>', '>\n')
        xml_string = xml_string.replace('<', '\n<')
        
        # Clean up multiple line breaks
        xml_string = re.sub(r'\n\n+', '\n', xml_string)
        
        # Add indentation
        lines = xml_string.split('\n')
        indent_level = 0
        result = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('</'):
                indent_level = max(0, indent_level - 1)
            
            result.append("    " * indent_level + line)
            
            if line.startswith('<') and not line.startswith('</') and not line.endswith('/>'):
                indent_level += 1
        
        return '\n'.join(result)

    def search_creative_id(self):
        """Search for a creative ID in the creative pulling database"""
        creative_id = self.creative_id_var.get().strip()
        
        if not creative_id:
            messagebox.showwarning("Warning", "Please enter a Creative ID")
            return
        
        # Disable button and show status
        self.search_creative_button.config(state='disabled')
        self.creative_search_results.config(state=tk.NORMAL)
        self.creative_search_results.delete(1.0, tk.END)
        self.creative_search_results.insert(tk.END, f"🔍 Searching for Creative ID: {creative_id}...")
        self.creative_search_results.config(state=tk.DISABLED)
        self.root.update()
        
        # Search in background thread
        threading.Thread(target=self._search_creative_id_thread, args=(creative_id,), daemon=True).start()
    
    def _search_creative_id_thread(self, creative_id):
        """Search for creative ID in background thread"""
        try:
            # Databricks connection
            connection_params = {
                "server_hostname": DATABRICKS_SERVER_HOSTNAME,
                "http_path": DATABRICKS_HTTP_PATH,
                "access_token": self.access_token
            }
            
            with sql.connect(**connection_params) as connection:
                with connection.cursor() as cursor:
                    # Query creative_pulling table for the specific creative_id
                    query = f"""
                    SELECT 
                        creative_id,
                        creation_date,
                        expire_date,
                        active
                    FROM {CREATIVE_PULLING_TABLE} 
                    WHERE creative_id = '{creative_id}'
                    ORDER BY creation_date DESC
                    """
                    
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    if results:
                        # Format results - only essential information
                        result_text = f"✅ FOUND: Creative ID '{creative_id}' is in the pulling queue\n\n"
                        
                        for i, row in enumerate(results, 1):
                            creative_id, creation_date, expire_date, active = row
                            
                            # Format dates
                            creation_str = creation_date.strftime('%Y-%m-%d %H:%M:%S') if creation_date else 'N/A'
                            expire_str = expire_date.strftime('%Y-%m-%d %H:%M:%S') if expire_date else 'N/A'
                            
                            result_text += f"📋 Record {i}:\n"
                            result_text += f"   🕒 Created Time: {creation_str}\n"
                            result_text += f"   ⏰ Expire Time: {expire_str}\n"
                            
                            # Check if expired and show status
                            if expire_date:
                                # Convert to naive datetime for comparison if needed
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
                    self.root.after(0, lambda: self._search_completed(result_text))
                    
        except Exception as e:
            error_msg = f"❌ Error searching for Creative ID: {str(e)}"
            self.root.after(0, lambda: self._search_completed(error_msg))
    
    def _search_completed(self, result_text):
        """Handle completed search"""
        self.search_creative_button.config(state='normal')
        self.creative_search_results.config(state=tk.NORMAL)
        self.creative_search_results.delete(1.0, tk.END)
        self.creative_search_results.insert(tk.END, result_text)
        self.creative_search_results.config(state=tk.DISABLED)
        
    def load_configuration(self):
        """Load Databricks access token - hardcoded with fallback dialog"""
        # Hardcoded token - update this with your current token
        # No hardcoded tokens
        
        try:
            # First, try to load from config file
            if os.path.exists("config.ini"):
                print("✅ Using hardcoded token")
                # return hardcoded_token.strip()  # Commented out hardcoded token
            
            # If hardcoded token is not set or invalid, prompt user
            print("⚠️ Hardcoded token not set or invalid, prompting user...")
            token = self.prompt_for_token()
            if token:
                print("✅ Token provided by user")
                return token
            
            # No token provided - exit
            messagebox.showerror("Token Required", "No valid Databricks token provided. App cannot continue.")
            sys.exit(1)
            
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Failed to load configuration: {str(e)}")
            sys.exit(1)
    
    def prompt_for_token(self):
        """Prompt user to enter Databricks token"""
        from tkinter import simpledialog
        
        # Create a simple dialog for token input
        token = simpledialog.askstring(
            "Databricks Token Required",
            "Please enter your Databricks Personal Access Token:\n\n" +
            "You can get this from:\n" +
            "Databricks → User Settings → Access Tokens\n\n" +
            "Token (starts with 'dapi'):",
            show='*'  # Hide the token input
        )
        
        if token and token.strip().startswith('dapi') and len(token.strip()) > 10:
            # Ask if user wants to save it
            save_token = messagebox.askyesno(
                "Save Token",
                "Would you like to save this token to config.ini for future use?\n\n" +
                "This will make it easier to run the app next time, but the token " +
                "will be stored in plain text on your computer."
            )
            
            if save_token:
                self.save_token_to_config(token.strip())
            
            return token.strip()
        
        return None
    
    def save_token_to_config(self, token):
        """Save token to config.ini file"""
        try:
            config = configparser.ConfigParser()
            
            # Read existing config if it exists
            if os.path.exists('config.ini'):
                config.read('config.ini')
            
            # Add/update DATABRICKS section
            if not config.has_section('DATABRICKS'):
                config.add_section('DATABRICKS')
            
            config.set('DATABRICKS', 'access_token', token)
            
            # Add APP section if it doesn't exist
            if not config.has_section('APP'):
                config.add_section('APP')
                config.set('APP', 'version', '1.0.0')
            
            # Write to file
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            
            print("✅ Token saved to config.ini")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not save token to config.ini: {e}")
    
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
import os
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime


def show_settings(app):
	"""Show settings dialog for bearer token management using a tabbed interface."""
	settings_window = tk.Toplevel(app.root)
	settings_window.title("Settings - Bearer Token Management")
	settings_window.geometry("800x600")
	settings_window.resizable(True, True)
	settings_window.transient(app.root)
	settings_window.grab_set()

	settings_window.update_idletasks()
	x = (settings_window.winfo_screenwidth() // 2) - (800 // 2)
	y = (settings_window.winfo_screenheight() // 2) - (600 // 2)
	settings_window.geometry(f"800x600+{x}+{y}")

	notebook = ttk.Notebook(settings_window)
	notebook.pack(expand=True, fill='both', padx=10, pady=10)

	savanna_tab = ttk.Frame(notebook, padding="10")
	databricks_tab = ttk.Frame(notebook, padding="10")

	notebook.add(savanna_tab, text='Savanna Token (Creative Pulling)')
	notebook.add(databricks_tab, text='Databricks Token (Main App)')

	_populate_savanna_tab(app, savanna_tab)
	_populate_databricks_tab(app, databricks_tab)


def _get_token_details(app, token):
	"""Decode JWT locally to avoid creating clients that may prompt."""
	try:
		import base64, json
		parts = token.split('.')
		if len(parts) != 3:
			return {"error": "Invalid JWT format"}
		payload_b64 = parts[1]
		padding = '=' * (-len(payload_b64) % 4)
		decoded = base64.urlsafe_b64decode(payload_b64 + padding)
		payload = json.loads(decoded.decode('utf-8'))
		expiry_time = datetime.fromtimestamp(payload.get('exp', 0))
		issued_time = datetime.fromtimestamp(payload.get('iat', 0))
		current_time = datetime.now()
		time_until_expiry = (expiry_time - current_time).total_seconds()
		hours_remaining = round(time_until_expiry / 3600, 1) if time_until_expiry > 0 else 0
		roles = payload.get('roles', [])
		roles_text = ", ".join(roles) if isinstance(roles, (list, tuple)) else str(roles)
		return {
			"valid": time_until_expiry > 0,
			"user": payload.get('user') or payload.get('email') or payload.get('sub', 'Unknown'),
			"roles": roles_text,
			"issued": issued_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
			"expires": expiry_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
			"remaining": f"{hours_remaining} hours" if hours_remaining > 0 else "Expired"
		}
	except Exception as e:
		return {"error": str(e)}


def _populate_savanna_tab(app, tab):
	current_frame = ttk.LabelFrame(tab, text="Current Token Information", padding="15")
	current_frame.pack(fill=tk.X, pady=(0, 20), expand=True)

	token_display_frame = ttk.Frame(current_frame)
	token_display_frame.pack(fill=tk.X, expand=True)

	def refresh_token_display():
		for widget in token_display_frame.winfo_children():
			widget.destroy()
		from savanna_bearer_client import SavannaBearerClient
		client = SavannaBearerClient()
		token = client.bearer_token
		if not token:
			ttk.Label(token_display_frame, text="❌ No Savanna token found in config.ini", foreground="red").pack(anchor=tk.W)
			return
		details = _get_token_details(app, token)
		if "error" in details:
			ttk.Label(token_display_frame, text=f"❌ Error: {details['error']}", foreground="red").pack(anchor=tk.W)
		else:
			status_text = "✅ Valid" if details['valid'] else "❌ Expired"
			status_color = "green" if details['valid'] else "red"
			ttk.Label(token_display_frame, text=f"Status: {status_text}", foreground=status_color).pack(anchor=tk.W)
			token_preview = f"{token[:20]}...{token[-20:]}"
			ttk.Label(token_display_frame, text=f"Token: {token_preview}", foreground="blue").pack(anchor=tk.W)
			ttk.Label(token_display_frame, text=f"User: {details['user']}").pack(anchor=tk.W)
			ttk.Label(token_display_frame, text=f"Roles: {details['roles']}").pack(anchor=tk.W)
			ttk.Label(token_display_frame, text=f"Issued: {details['issued']}").pack(anchor=tk.W)
			ttk.Label(token_display_frame, text=f"Expires: {details['expires']}").pack(anchor=tk.W)
			time_remaining_color = "green" if details['valid'] else "red"
			ttk.Label(token_display_frame, text=f"Time Remaining: {details['remaining']}", foreground=time_remaining_color).pack(anchor=tk.W)

	refresh_token_display()

	update_frame = ttk.LabelFrame(tab, text="Update Bearer Token", padding="15")
	update_frame.pack(fill=tk.X, pady=(0, 20), expand=True)

	token_var = tk.StringVar()
	ttk.Label(update_frame, text="📁 Upload HAR file to extract token:").pack(anchor=tk.W, pady=(0, 5))

	def upload_har_file():
		file_path = filedialog.askopenfilename(filetypes=[("HAR files", "*.har")])
		if file_path:
			token = app.extract_token_from_har(file_path)
			if token:
				token_var.set(token)
				messagebox.showinfo("Success", "Token extracted from HAR file.")
			else:
				messagebox.showwarning("Not Found", "No bearer token found in the HAR file.")

	ttk.Button(update_frame, text="Upload HAR File", command=upload_har_file).pack(anchor=tk.W, pady=(0, 10))

	ttk.Label(update_frame, text="Enter new bearer token:").pack(anchor=tk.W, pady=(5, 5))
	token_entry = ttk.Entry(update_frame, textvariable=token_var, width=80, show="*")
	token_entry.pack(fill=tk.X, expand=True, pady=(0, 10))

	button_frame = ttk.Frame(update_frame)
	button_frame.pack(fill=tk.X, expand=True)

	def test_savanna_token():
		new_token = token_var.get().strip()
		if not new_token:
			messagebox.showwarning("Input Required", "Please enter a token to test.")
			return
		details = _get_token_details(app, new_token)
		if "error" in details:
			messagebox.showerror("Test Failed", f"Error: {details['error']}")
		else:
			details_str = "\n".join([f"{k.capitalize()}: {v}" for k, v in details.items()])
			messagebox.showinfo("Token Test Result", f"Token Details:\n\n{details_str}")

	def update_savanna_token():
		new_token = token_var.get().strip()
		if not new_token:
			messagebox.showwarning("Input Required", "Please enter a token to update.")
			return
		try:
			config_path = os.path.join(os.path.expanduser("~"), ".creative_pull_app", "config.ini")
			config = configparser.ConfigParser()
			config.read(config_path)
			if 'SAVANNA' not in config:
				config.add_section('SAVANNA')
			config['SAVANNA']['bearer_token'] = new_token
			with open(config_path, 'w') as configfile:
				config.write(configfile)
			if hasattr(app, 'savanna_client'):
				app.savanna_client.bearer_token = new_token
			messagebox.showinfo("Success", "Savanna token updated successfully.")
			refresh_token_display()
			token_var.set("")
		except Exception as e:
			messagebox.showerror("Error", f"Failed to update token: {e}")

	ttk.Button(button_frame, text="🧪 Test Token", command=test_savanna_token).pack(side=tk.LEFT, padx=(0, 10))
	ttk.Button(button_frame, text="💾 Update Token", command=update_savanna_token).pack(side=tk.LEFT)


def _populate_databricks_tab(app, tab):
	current_frame = ttk.LabelFrame(tab, text="Current Token Information", padding="15")
	current_frame.pack(fill=tk.X, pady=(0, 20), expand=True)

	token_display_frame = ttk.Frame(current_frame)
	token_display_frame.pack(fill=tk.X, expand=True)

	def refresh_databricks_display():
		for widget in token_display_frame.winfo_children():
			widget.destroy()
		if hasattr(app, 'access_token') and app.access_token:
			databricks_token_preview = f"{app.access_token[:20]}...{app.access_token[-20:]}"
			ttk.Label(token_display_frame, text=f"🔗 Token: {databricks_token_preview}", foreground="blue").pack(anchor=tk.W)
			ttk.Label(token_display_frame, text="✅ Status: Valid (App is working)", foreground="green").pack(anchor=tk.W)
			ttk.Label(token_display_frame, text="ℹ️ Note: Databricks tokens don't expire automatically.", foreground="gray").pack(anchor=tk.W)
		else:
			ttk.Label(token_display_frame, text="❌ No Databricks token found.", foreground="red").pack(anchor=tk.W)

	refresh_databricks_display()

	update_frame = ttk.LabelFrame(tab, text="Update Databricks Token", padding="15")
	update_frame.pack(fill=tk.X, pady=(0, 20), expand=True)

	ttk.Label(update_frame, text="Enter new Databricks PAT:").pack(anchor=tk.W, pady=(0, 5))
	token_var = tk.StringVar()
	token_entry = ttk.Entry(update_frame, textvariable=token_var, width=80, show="*")
	token_entry.pack(fill=tk.X, pady=(0, 10))

	button_frame = ttk.Frame(update_frame)
	button_frame.pack(fill=tk.X)

	def test_databricks_token():
		new_token = token_var.get().strip()
		if not new_token:
			messagebox.showwarning("Input Required", "Please enter a token to test.")
			return
		if new_token.startswith("dapi") and len(new_token) > 20:
			messagebox.showinfo("Test Result", "✅ Token format appears valid.\n\nNote: This is a basic format check. A full connection test requires an app restart.")
		else:
			messagebox.showerror("Test Result", "❌ Token format appears invalid. It should start with 'dapi'.")

	def update_databricks_token():
		new_token = token_var.get().strip()
		if not (new_token.startswith("dapi") and len(new_token) > 20):
			messagebox.showwarning("Invalid Token", "Please enter a valid Databricks token (starts with 'dapi').")
			return
		try:
			from config.app_config import save_token_to_config
			save_token_to_config(new_token)
			app.access_token = new_token
			messagebox.showinfo("Success", "Databricks token updated successfully.\nChanges will be fully applied on next app start.")
			refresh_databricks_display()
			token_var.set("")
		except Exception as e:
			messagebox.showerror("Error", f"Failed to update token: {e}")

	ttk.Button(button_frame, text="🧪 Test Token", command=test_databricks_token).pack(side=tk.LEFT, padx=(0, 10))
	ttk.Button(button_frame, text="💾 Update Token", command=update_databricks_token).pack(side=tk.LEFT)



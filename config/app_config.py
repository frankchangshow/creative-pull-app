import os
import sys
import configparser
from tkinter import messagebox, simpledialog


def load_configuration():
	"""Load Databricks access token from config file or prompt user"""
	try:
		# First, try to load from config file - check multiple locations
		config = configparser.ConfigParser()
		config_paths = [
			"config.ini",  # Current directory
			os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.ini"),  # Module directory parent
			os.path.join(os.path.expanduser("~"), ".creative_pull_app", "config.ini"),  # User home directory
			os.path.join(os.getcwd(), "config.ini")  # Working directory
		]
		
		for config_path in config_paths:
			print(f"🔍 Checking for config at: {config_path}")
			if os.path.exists(config_path):
				print(f"✅ Found config file at: {config_path}")
				config.read(config_path)
				if config.has_section("DATABRICKS") and config.has_option("DATABRICKS", "access_token"):
					saved_token = config.get("DATABRICKS", "access_token")
					if saved_token and saved_token.startswith("dapi") and len(saved_token.strip()) > 20:
						print("✅ Using saved token from config.ini")
						return saved_token.strip()
					else:
						print(f"⚠️ Token in config is invalid: {saved_token[:10]}...")
				else:
					print("⚠️ Config file exists but no valid DATABRICKS section found")
			else:
				print(f"❌ Config not found at: {config_path}")
		
		# If no valid token in config, prompt user
		print("⚠️ No valid token found, prompting user...")
		token = prompt_for_token()
		if token:
			print("✅ Token provided by user")
			return token
		
		# No token provided - exit
		messagebox.showerror("Token Required", "No valid Databricks token provided. App cannot continue.")
		sys.exit(1)
		
	except Exception as e:
		messagebox.showerror("Configuration Error", f"Failed to load configuration: {str(e)}")
		sys.exit(1)


def prompt_for_token():
	"""Prompt user to enter Databricks token"""
	# Create a simple dialog for token input
	token = simpledialog.askstring(
		"Databricks Token Required",
		"Please enter your Databricks Personal Access Token:\n\n"
		"You can get this from:\n"
		"Databricks → User Settings → Access Tokens\n\n"
		"Token (starts with 'dapi'):",
		show='*'  # Hide the token input
	)
	
	if token and token.strip().startswith('dapi') and len(token.strip()) > 10:
		# Ask if user wants to save it
		save_token = messagebox.askyesno(
			"Save Token",
			"Would you like to save this token to config.ini for future use?\n\n"
			"This will make it easier to run the app next time, but the token "
			"will be stored in plain text on your computer."
		)
		
		if save_token:
			save_token_to_config(token.strip())
		
		return token.strip()
	
	return None


def save_token_to_config(token: str) -> None:
	"""Save token to config.ini file"""
	try:
		config = configparser.ConfigParser()
		
		# Try to read existing config from multiple locations
		config_paths = [
			"config.ini",  # Current directory
			os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.ini"),  # Module directory parent
			os.path.join(os.path.expanduser("~"), ".creative_pull_app", "config.ini"),  # User home directory
			os.path.join(os.getcwd(), "config.ini")  # Working directory
		]
		
		for config_path in config_paths:
			if os.path.exists(config_path):
				config.read(config_path)
				print(f"✅ Reading existing config from: {config_path}")
				break
		
		# Add/update DATABRICKS section
		if not config.has_section('DATABRICKS'):
			config.add_section('DATABRICKS')
		
		config.set('DATABRICKS', 'access_token', token)
		
		# Add APP section if it doesn't exist
		if not config.has_section('APP'):
			config.add_section('APP')
			config.set('APP', 'version', '1.0.0')
		
		# Try to save to multiple locations, prefer user home directory
		save_paths = [
			os.path.join(os.path.expanduser("~"), ".creative_pull_app", "config.ini"),  # User home (preferred)
			"config.ini",  # Current directory
			os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.ini"),  # Module directory parent
		]
		
		saved = False
		for save_path in save_paths:
			try:
				# Create directory if it doesn't exist
				dirname = os.path.dirname(save_path)
				if dirname:
					os.makedirs(dirname, exist_ok=True)
				with open(save_path, 'w') as configfile:
					config.write(configfile)
				print(f"✅ Token saved to: {save_path}")
				saved = True
				break
			except Exception as e:
				print(f"⚠️ Could not save to {save_path}: {e}")
				continue
		
		if not saved:
			print("❌ Warning: Could not save token to any location")
		
	except Exception as e:
		print(f"⚠️ Warning: Could not save token to config.ini: {e}")



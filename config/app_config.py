import os
import sys
import configparser
from tkinter import messagebox, simpledialog


def _resolve_config_path() -> str:
	"""Return canonical config.ini path.

	Order:
	1) CREATIVE_PULL_APP_CONFIG env var (file path or directory)
	2) ~/.creative_pull_app/config.ini

	Ensures parent directory exists.
	"""
	# Env override
	env_path = os.environ.get('CREATIVE_PULL_APP_CONFIG')
	if env_path:
		if os.path.isdir(env_path):
			env_path = os.path.join(env_path, 'config.ini')
		parent = os.path.dirname(env_path)
		if parent:
			os.makedirs(parent, exist_ok=True)
		return env_path

	# Default
	default_dir = os.path.join(os.path.expanduser('~'), '.creative_pull_app')
	os.makedirs(default_dir, exist_ok=True)
	return os.path.join(default_dir, 'config.ini')



def load_configuration():
	"""Load Databricks access token from canonical config path or prompt user"""
	try:
		config_path = _resolve_config_path()
		print(f"🔍 Using canonical config path: {config_path}")
		config = configparser.ConfigParser()
		if os.path.isfile(config_path):
			config.read(config_path)
			# Apply optional CA bundle settings early, if provided in config
			_apply_ca_bundle_settings(config)
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
			print("❌ Config file not found; will prompt user and then save it here.")
			# Even if config does not exist yet, honor env-based CA bundle settings
			_apply_ca_bundle_settings(None)
		
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



def _apply_ca_bundle_settings(config: configparser.ConfigParser | None) -> None:
	"""Apply optional CA bundle settings to process env for TLS verification.

	Order of precedence:
	1) CREATIVE_PULL_APP_CA_BUNDLE environment variable (path to a PEM bundle)
	2) [APP] ca_bundle_path in config.ini (if provided)

	If the provided path exists, sets REQUESTS_CA_BUNDLE and SSL_CERT_FILE so
	requests/urllib3 and libraries that honor these env vars trust the bundle.
	"""
	try:
		# 1) Environment override
		env_bundle = os.environ.get('CREATIVE_PULL_APP_CA_BUNDLE')
		if env_bundle:
			_bundle_path = os.path.expanduser(env_bundle)
			if os.path.isfile(_bundle_path):
				os.environ['REQUESTS_CA_BUNDLE'] = _bundle_path
				os.environ['SSL_CERT_FILE'] = _bundle_path
				print(f"🔐 Using CA bundle from CREATIVE_PULL_APP_CA_BUNDLE: {_bundle_path}")
				return
			else:
				print(f"⚠️ CREATIVE_PULL_APP_CA_BUNDLE path not found: {_bundle_path}")

		# 2) Config setting
		if config is not None and config.has_section('APP') and config.has_option('APP', 'ca_bundle_path'):
			cfg_bundle = os.path.expanduser(config.get('APP', 'ca_bundle_path').strip())
			if cfg_bundle:
				if os.path.isfile(cfg_bundle):
					os.environ['REQUESTS_CA_BUNDLE'] = cfg_bundle
					os.environ['SSL_CERT_FILE'] = cfg_bundle
					print(f"🔐 Using CA bundle from config [APP].ca_bundle_path: {cfg_bundle}")
				else:
					print(f"⚠️ Config [APP].ca_bundle_path not found: {cfg_bundle}")

		# 3) macOS default fallback if nothing set
		if not os.environ.get('REQUESTS_CA_BUNDLE') and sys.platform == 'darwin':
			mac_default = '/etc/ssl/cert.pem'
			if os.path.isfile(mac_default):
				os.environ.setdefault('REQUESTS_CA_BUNDLE', mac_default)
				os.environ.setdefault('SSL_CERT_FILE', mac_default)
				print(f"🔐 Using macOS default CA bundle: {mac_default}")
	except Exception as e:
		print(f"⚠️ Failed to apply CA bundle settings: {e}")

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
	"""Save token to canonical config.ini path"""
	try:
		config = configparser.ConfigParser()
		config_path = _resolve_config_path()
		# Read existing if present
		if os.path.isfile(config_path):
			config.read(config_path)
			print(f"✅ Reading existing config from: {config_path}")
		# Ensure sections
		if not config.has_section('DATABRICKS'):
			config.add_section('DATABRICKS')
		config.set('DATABRICKS', 'access_token', token)
		if not config.has_section('APP'):
			config.add_section('APP')
			config.set('APP', 'version', '1.0.0')
		# Write to canonical path
		os.makedirs(os.path.dirname(config_path), exist_ok=True)
		with open(config_path, 'w') as configfile:
			config.write(configfile)
		print(f"✅ Token saved to: {config_path}")
		
	except Exception as e:
		print(f"⚠️ Warning: Could not save token to config.ini: {e}")



def set_ca_bundle_path_in_config(ca_path: str) -> None:
	"""Persist CA bundle path to canonical config.ini under [APP].ca_bundle_path."""
	try:
		ca_path = os.path.expanduser(ca_path or '').strip()
		if not ca_path:
			return
		config_path = _resolve_config_path()
		config = configparser.ConfigParser()
		if os.path.isfile(config_path):
			config.read(config_path)
		# Ensure sections
		if not config.has_section('APP'):
			config.add_section('APP')
		config.set('APP', 'ca_bundle_path', ca_path)
		os.makedirs(os.path.dirname(config_path), exist_ok=True)
		with open(config_path, 'w') as f:
			config.write(f)
		print(f"✅ Saved CA bundle path to config: {config_path}")
	except Exception as e:
		print(f"⚠️ Failed to save CA bundle path: {e}")


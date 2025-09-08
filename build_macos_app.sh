#!/bin/bash
set -euo pipefail

APP_NAME="CreativePullApp"
ENTRY="creative_previewer_app_webview.py"
VENV=".venv_build"

echo "=== Building $APP_NAME macOS app ==="

# Clean
rm -rf dist build "$APP_NAME.spec" "$VENV"

# venv
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Build (onedir, no icon)
pyinstaller \
  --name "$APP_NAME" \
  --windowed \
  --osx-bundle-identifier "com.digitalturbine.creativepull" \
  --hidden-import tkinter \
  --add-data "clients:clients" \
  --add-data "config:config" \
  --add-data "databricks_job_templates:databricks_job_templates" \
  --add-data "services:services" \
  --add-data "ui:ui" \
  --add-data "utils:utils" \
  --add-data "savanna_bearer_client.py:." \
  "$ENTRY"

echo "Build complete: dist/$APP_NAME.app"
echo "Tip: if Gatekeeper blocks it on another Mac, run: xattr -dr com.apple.quarantine dist/$APP_NAME.app"

deactivate

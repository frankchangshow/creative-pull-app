#!/bin/bash
# ==============================================================================
# Definitive Build Script for Creative Previewer App on macOS
#
# This script creates a consistent, reliable, and distributable macOS
# application bundle. It uses a virtual environment to ensure that the build
# is isolated and uses only the specified dependencies.
#
# USAGE:
#   ./build_macos_app.sh
# ==============================================================================

# --- Configuration ---
set -e # Exit immediately if a command exits with a non-zero status.

APP_NAME="Creative_Previewer_App"
MAIN_SCRIPT="creative_previewer_app_webview.py"
ICON_FILE="app_icon.icns"
VENV_DIR="build_venv"

# --- 1. Forceful Cleanup ---
echo "🧹 Step 1/5: Cleaning up previous build artifacts..."
rm -rf build/ dist/ "$VENV_DIR"/ "$APP_NAME.app"/ "$APP_NAME"_Distribution/
rm -f "$APP_NAME.spec" *.zip
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "✅ Cleanup complete."
echo

# --- 2. Create Virtual Environment ---
echo "🐍 Step 2/5: Creating a fresh Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment created and activated."
echo

# --- 3. Install Dependencies ---
echo "📦 Step 3/5: Installing dependencies from requirements.txt..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo "✅ Dependencies installed successfully."
# Optional: Verify key packages
echo "🔍 Verifying key packages:"
pip3 freeze | grep -E "databricks-sql-connector|requests|pyinstaller|numpy"
echo

# --- 4. Run PyInstaller Build ---
echo "🛠️  Step 4/5: Building the application with PyInstaller..."
pyinstaller \
    --name "$APP_NAME" \
    --windowed \
    --clean \
    --noconfirm \
    --icon="$ICON_FILE" \
    --collect-all numpy \
    --exclude-module matplotlib \
    --exclude-module scipy \
    --log-level=INFO \
    "$MAIN_SCRIPT"

echo "✅ PyInstaller build process complete."
echo

# --- 5. Package for Distribution ---
echo "📦 Step 5/5: Packaging the final application for distribution..."

# Create a distribution directory
DIST_DIR="${APP_NAME}_Distribution"
mkdir -p "$DIST_DIR"

# Copy the .app bundle and other useful files directly from the build output
cp -r "dist/$APP_NAME.app" "$DIST_DIR/"
cp "README.md" "$DIST_DIR/"
cp "requirements.txt" "$DIST_DIR/"

# Create a timestamped ZIP archive
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FINAL_ZIP_NAME="${APP_NAME}_macOS_${TIMESTAMP}.zip"
zip -r "$FINAL_ZIP_NAME" "$DIST_DIR"

echo "✅ Distribution package created: $FINAL_ZIP_NAME"
echo

# --- Deactivate Virtual Environment ---
deactivate
echo "🚪 Virtual environment deactivated."
echo

# --- 6. Final Cleanup ---
echo "🧹 Step 6/6: Removing all temporary build files..."
rm -rf build/
rm -rf dist/
rm -rf "$DIST_DIR"/
rm -rf "$VENV_DIR"/
rm -f "$APP_NAME.spec"
echo "✅ Final cleanup complete."
echo

# --- Final Summary ---
ZIP_SIZE=$(du -sh "$FINAL_ZIP_NAME" | awk '{print $1}')
echo "🎉 BUILD SUCCEEDED! 🎉"
echo "====================================================="
echo "The final distributable ZIP file has been created:"
echo "  -> $FINAL_ZIP_NAME (Size: $ZIP_SIZE)"
echo
echo "All temporary build files have been removed."
echo "====================================================="

#!/bin/bash

echo "🍎 Building Creative Pull App for macOS (Fixed numpy issue)..."

# Clean up previous builds
rm -rf build dist

# Install PyInstaller if not already installed
pip3 install pyinstaller

# Build the macOS app with proper numpy handling
pyinstaller --onefile --windowed --name "Creative_Pull_App_macOS" \
    --hidden-import numpy \
    --hidden-import numpy.core \
    --hidden-import numpy.core.multiarray \
    --collect-all numpy \
    --exclude-module numpy.tests \
    --exclude-module numpy.f2py \
    --exclude-module numpy.distutils \
    creative_previewer_app_webview.py

# Check if build was successful
if [ -f "dist/Creative_Pull_App_macOS" ]; then
    echo "✅ Build successful! App created at: dist/Creative_Pull_App_macOS"
    
    # Create distribution folder
    mkdir -p "Creative_Pull_App_macOS_v4"
    cp "dist/Creative_Pull_App_macOS" "Creative_Pull_App_macOS_v4/"
    cp "requirements.txt" "Creative_Pull_App_macOS_v4/"
    cp "README.md" "Creative_Pull_App_macOS_v4/"
    
    # Create launcher script
    cat > "Creative_Pull_App_macOS_v4/Launch_App.sh" << 'LAUNCHER'
#!/bin/bash
echo "🚀 Starting Creative Pull App..."
echo "If you get a security warning, go to:"
echo "System Preferences → Security & Privacy → General → Allow Anyway"
echo ""
./Creative_Pull_App_macOS
LAUNCHER
    
    chmod +x "Creative_Pull_App_macOS_v4/Launch_App.sh"
    
    # Create ZIP archive
    zip -r "Creative_Pull_App_macOS_v4.zip" "Creative_Pull_App_macOS_v4/"
    
    echo "📦 Distribution package created: Creative_Pull_App_macOS_v4.zip"
    echo "📁 Contents: Creative_Pull_App_macOS_v4/"
else
    echo "❌ Build failed!"
    exit 1
fi

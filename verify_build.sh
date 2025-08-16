#!/bin/bash

echo "🔍 Creative Previewer App - Build Verification Script"
echo "=================================================="

# Check if app bundle exists
if [ ! -d "Creative_Previewer_App.app" ]; then
    echo "❌ App bundle not found! Please run build_macos_app.sh first."
    exit 1
fi

echo "✅ App bundle found"

# Check app bundle structure
echo ""
echo "📁 App Bundle Structure:"
echo "   Creative_Previewer_App.app/"
echo "   ├── Contents/"
echo "   │   ├── MacOS/"
echo "   │   │   └── Creative_Previewer_App (executable)"
echo "   │   └── Info.plist"
echo "   └── ..."

# Verify main executable
if [ -f "Creative_Previewer_App.app/Contents/MacOS/Creative_Previewer_App" ]; then
    echo "✅ Main executable found"
    EXECUTABLE_SIZE=$(du -sh "Creative_Previewer_App.app/Contents/MacOS/Creative_Previewer_App" | cut -f1)
    echo "   Size: $EXECUTABLE_SIZE"
else
    echo "❌ Main executable missing!"
fi

# Check app bundle size
APP_SIZE=$(du -sh "Creative_Previewer_App.app" | cut -f1)
echo "📱 Total app bundle size: $APP_SIZE"

# Check Info.plist
if [ -f "Creative_Previewer_App.app/Contents/Info.plist" ]; then
    echo "✅ Info.plist found"
    BUNDLE_VERSION=$(grep -A1 "CFBundleVersion" "Creative_Previewer_App.app/Contents/Info.plist" | tail -1 | sed 's/.*<string>\(.*\)<\/string>.*/\1/')
    echo "   Version: $BUNDLE_VERSION"
else
    echo "❌ Info.plist missing!"
fi

# Check distribution package
if [ -d "Creative_Previewer_App_Distribution" ]; then
    echo "✅ Distribution package found"
    
    # Check required files
    REQUIRED_FILES=(
        "BUILD_INFO.txt"
        "INSTALL_INSTRUCTIONS.txt"
        "requirements.txt"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ -f "Creative_Preview_App_Distribution/$file" ]; then
            echo "   ✅ $file found"
        else
            echo "   ❌ $file missing"
        fi
    done
else
    echo "❌ Distribution package not found!"
fi

# Check for ZIP archive
ZIP_FILES=$(ls -1 Creative_Previewer_App_macOS_*.zip 2>/dev/null | wc -l)
if [ $ZIP_FILES -gt 0 ]; then
    echo "✅ ZIP archive(s) found: $ZIP_FILES"
    ls -lh Creative_Previewer_App_macOS_*.zip
else
    echo "❌ No ZIP archives found"
fi

# Check for any leftover build artifacts
echo ""
echo "🧹 Checking for leftover build artifacts..."
if [ -d "build" ]; then
    echo "⚠️  'build' directory found (should be cleaned up)"
fi

if [ -d "dist" ]; then
    echo "⚠️  'dist' directory found (should be cleaned up)"
fi

if [ -f "*.spec" ]; then
    echo "⚠️  '.spec' file found (should be cleaned up)"
fi

# Check Python cache
PYCACHE_COUNT=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l)
if [ $PYCACHE_COUNT -gt 0 ]; then
    echo "⚠️  $PYCACHE_COUNT Python cache directories found"
fi

echo ""
echo "🎯 Build Verification Complete!"
echo "=============================="

if [ -f "Creative_Previewer_App.app/Contents/MacOS/Creative_Previewer_App" ]; then
    echo "✅ App bundle appears to be complete and ready for testing"
    echo ""
    echo "🚀 To test the app:"
    echo "   Double-click Creative_Previewer_App.app"
    echo ""
    echo "📋 Build details saved in BUILD_INFO.txt"
else
    echo "❌ App bundle appears to be incomplete"
    echo "   Please check the build logs and try again"
fi

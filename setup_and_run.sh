#!/bin/bash
# Setup script for BenX AI

echo "=========================================="
echo "BenX AI - Setup Script"
echo "=========================================="
echo ""

# Check if API key is already set
if [ -n "$GROQ_API_KEY" ] || [ -n "$GROQ_KEY" ]; then
    echo "✅ API key already configured in environment"
else
    echo "⚠️  No API key found in environment"
    echo ""
    echo "To set up your Groq API key:"
    echo "1. Get a free API key from: https://console.groq.com/keys"
    echo "2. Run one of these commands:"
    echo ""
    echo "   # Temporary (current session only):"
    echo "   export GROQ_API_KEY='your_key_here'"
    echo ""
    echo "   # Permanent (add to ~/.bashrc or ~/.zshrc):"
    echo "   echo 'export GROQ_API_KEY=\"your_key_here\"' >> ~/.bashrc"
    echo "   source ~/.bashrc"
    echo ""
    read -p "Do you want to set it now? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Groq API key: " api_key
        export GROQ_API_KEY="$api_key"
        echo "✅ API key set for this session"
        echo ""
        echo "To make it permanent, add this to your ~/.bashrc:"
        echo "export GROQ_API_KEY=\"$api_key\""
    fi
fi

echo "🔧 Installing Python dependencies..."
cd /home/natesh/Downloads/Ben
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo ""
echo "✅ Dependencies installed!"
echo "=========================================="
echo "Running BenX AI..."
echo "=========================================="
echo ""

# System deps reminder
echo "💡 Install system deps if needed:"
echo "Arch: sudo pacman -S gtk4 libadwaita python-gobject tesseract grim android-tools"
echo "Ubuntu: sudo apt install libgtk-4-1 libadwaita-1-0 python3-gi tesseract-ocr grim adb"
echo ""
echo "📱 Mobile Setup:"
echo "1. Enable Developer Options + USB Debugging on Android"
echo "2. Connect phone: adb devices (authorize USB)"
echo "3. python jarvis_ai/mobile_automation.py test"

python3 benx.py "$@"


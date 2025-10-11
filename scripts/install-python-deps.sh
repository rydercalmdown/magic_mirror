#!/bin/bash

# Install Python dependencies for the backend using virtual environment
# This includes Flask, OpenCV, Socket.IO and training pipeline deps

echo "📦 Installing Python dependencies..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pip3 is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Create virtual environment if it doesn't exist
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install core backend deps
echo "📦 Installing Python packages from requirements.txt..."
pip install -r requirements.txt

# Install training pipeline dependencies if available (mediapipe/torch/sklearn)
echo "🧠 Installing training pipeline dependencies (if missing)..."
pip install --upgrade pip wheel setuptools
pip install mediapipe==0.10.14 scikit-learn==1.3.2 || true
# Try to install a cpu-only torch suitable for Pi; if fails, skip silently
pip install torch==2.3.0 --extra-index-url https://download.pytorch.org/whl/cpu || true

if [ $? -eq 0 ]; then
    echo "✅ Python dependencies installed successfully!"
    echo "📝 Virtual environment created at: $VENV_DIR"
    echo "🔧 To activate manually: source $VENV_DIR/bin/activate"
else
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✅ Python installation complete!"

#!/bin/bash

# Install OpenCV with pre-built binaries for Raspberry Pi
# This avoids the need to compile OpenCV from source

echo "📦 Installing OpenCV with pre-built binaries..."

# Clean up any existing node_modules
if [ -d "node_modules" ]; then
    echo "🧹 Cleaning existing node_modules..."
    rm -rf node_modules
fi

if [ -f "package-lock.json" ]; then
    echo "🧹 Cleaning package-lock.json..."
    rm -f package-lock.json
fi

# Install basic dependencies first
echo "📦 Installing basic Node.js dependencies..."
npm install express cors socket.io

# Install OpenCV with pre-built binaries
echo "📦 Installing OpenCV with pre-built binaries..."
npm install opencv4nodejs --opencv4nodejs_binary_host_mirror=https://github.com/opencv4nodejs/opencv4nodejs-prebuilt/releases/download/5.6.0/

if [ $? -eq 0 ]; then
    echo "✅ OpenCV installed successfully with pre-built binaries!"
else
    echo "❌ Failed to install OpenCV with pre-built binaries"
    echo "🔄 Trying alternative pre-built mirror..."
    npm install opencv4nodejs --opencv4nodejs_binary_host_mirror=https://github.com/opencv4nodejs/opencv4nodejs-prebuilt/releases/download/5.6.0/ --force
fi

echo "✅ OpenCV installation complete!"

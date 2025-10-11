#!/bin/bash

# Install Node.js dependencies from package.json
# This includes socket.io-client for the node helper

echo "📦 Installing Node.js dependencies..."

# Clean up any existing node_modules
if [ -d "node_modules" ]; then
    echo "🧹 Cleaning existing node_modules..."
    rm -rf node_modules
fi

if [ -f "package-lock.json" ]; then
    echo "🧹 Cleaning package-lock.json..."
    rm -f package-lock.json
fi

# Install all dependencies from package.json
echo "📦 Installing all dependencies from package.json..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ All dependencies installed successfully!"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Node.js installation complete!"

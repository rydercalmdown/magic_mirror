#!/bin/bash

# Comprehensive setup script for Magic Mirror Backend
# This script installs dependencies, sets up PM2, and optionally configures systemd

PROJECT_DIR="/Users/ryder/Code/rydercalmdown/magic_mirror"
BACKEND_APP_NAME="magic-mirror-backend"

echo "🚀 Setting up Magic Mirror Backend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed. Please install npm first."
    exit 1
fi

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd "$PROJECT_DIR"
npm install express cors

# Install PM2 globally if not already installed
if ! command -v pm2 &> /dev/null; then
    echo "📦 Installing PM2 globally..."
    npm install -g pm2
else
    echo "✅ PM2 is already installed"
fi

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p "$PROJECT_DIR/logs"

# Start the backend with PM2
echo "🚀 Starting Magic Mirror Backend with PM2..."
pm2 start ecosystem.config.js

# Save PM2 configuration
echo "💾 Saving PM2 configuration..."
pm2 save

# Setup PM2 to start on boot
echo "🔄 Setting up PM2 to start on boot..."
pm2 startup

echo ""
echo "✅ Magic Mirror Backend setup complete!"
echo ""
echo "📋 Available commands:"
echo "  make start-backend    - Start the backend daemon"
echo "  make stop-backend     - Stop the backend daemon"
echo "  make restart-backend  - Restart the backend daemon"
echo "  make status-backend   - Check backend status"
echo "  make logs-backend     - View backend logs"
echo ""
echo "🌐 Backend API is running at: http://localhost:5000"
echo "🔍 Health check: http://localhost:5000/api/health"
echo ""
echo "💡 To set up systemd service (optional): make setup-systemd"
echo "💡 To view real-time logs: pm2 logs $BACKEND_APP_NAME"
echo "💡 To monitor processes: pm2 monit"

#!/bin/bash

# Setup script for Magic Mirror Backend systemd service
# This script installs the systemd service for auto-start on boot

PROJECT_DIR="/Users/ryder/Code/rydercalmdown/magic_mirror"
SERVICE_FILE="magic-mirror-backend.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "Setting up Magic Mirror Backend systemd service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "Error: PM2 is not installed. Please install PM2 first:"
    echo "npm install -g pm2"
    exit 1
fi

# Copy service file to systemd directory
echo "Installing systemd service file..."
cp "$PROJECT_DIR/$SERVICE_FILE" "$SYSTEMD_DIR/"

# Update the service file with the correct user and working directory
sed -i.bak "s|User=ryder|User=$(whoami)|g" "$SYSTEMD_DIR/$SERVICE_FILE"
sed -i.bak "s|WorkingDirectory=/Users/ryder/Code/rydercalmdown/magic_mirror|WorkingDirectory=$PROJECT_DIR|g" "$SYSTEMD_DIR/$SERVICE_FILE"

# Reload systemd and enable the service
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling Magic Mirror Backend service..."
systemctl enable magic-mirror-backend.service

echo "Systemd service installed and enabled!"
echo ""
echo "To start the service: sudo systemctl start magic-mirror-backend"
echo "To stop the service: sudo systemctl stop magic-mirror-backend"
echo "To check status: sudo systemctl status magic-mirror-backend"
echo "To view logs: sudo journalctl -u magic-mirror-backend -f"

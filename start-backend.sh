#!/bin/bash

# Start script for MMM-HabitTracker backend
echo "Starting MMM-HabitTracker Backend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install express cors
fi

# Start the backend server
echo "Starting backend server on http://localhost:5000"
node backend.js

#!/bin/bash

# Install system dependencies for Python backend with OpenCV

sudo apt update

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install OpenCV and dependencies
sudo apt install -y python3-opencv libopencv-dev

# Install additional dependencies for OpenCV
sudo apt install -y build-essential cmake pkg-config
sudo apt install -y libjpeg-dev libtiff5-dev libpng-dev
sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt install -y libxvidcore-dev libx264-dev
sudo apt install -y libgtk-3-dev libatlas-base-dev gfortran

# Install USB webcam support
sudo apt install -y v4l-utils

echo "✅ Python, OpenCV and dependencies installed"
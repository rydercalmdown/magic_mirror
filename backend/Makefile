# Backend Makefile for Magic Mirror Habit Tracker
# Handles uv-based Python dependency management and running

.PHONY: build run clean install-uv

# Default target
all: build

# Install uv if not present
install-uv:
	@echo "🔧 Checking for uv..."
	@which uv >/dev/null 2>&1 || (echo "📦 Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)

# Build/install dependencies with uv
build: install-uv
	@echo "📦 Installing Python dependencies with uv..."
	@uv sync
	@echo "✅ Backend dependencies installed"

# Run the backend server
run: build
	@echo "🧹 Clearing old clips/results..."
	@rm -rf data/clips/* 2>/dev/null || true
	@rm -rf data/results/* 2>/dev/null || true
	@echo "🚀 Starting backend server on http://localhost:8000"
	@uv run python app.py

# Clean up uv environment
clean:
	@echo "🧹 Cleaning up backend environment..."
	@rm -rf .venv
	@echo "✅ Backend environment cleaned"

# Development mode with auto-reload (if needed later)
dev: build
	@echo "🚀 Starting backend in development mode on http://localhost:8000..."
	@uv run python app.py

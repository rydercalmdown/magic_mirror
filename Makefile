# Makefile for Magic Mirror project

# Variables
BACKEND_APP_NAME = magic-mirror-backend

.PHONY: install run clean start-backend stop-backend restart-backend status-backend logs-backend setup-backend-daemon setup setup-systemd

# Install all dependencies and setup backend
install:
	@echo "🚀 Installing dependencies and setting up backend..."
	@echo "📦 Installing system dependencies..."
	@bash ./scripts/install-deps.sh
	@echo "📦 Installing Python dependencies..."
	@bash ./scripts/install-python-deps.sh
	@echo "📦 Installing Node.js dependencies..."
	@bash ./scripts/install-opencv.sh
	@echo "🔧 Setting up backend daemon..."
	@bash ./scripts/setup-backend.sh
	@echo "✅ Installation and setup complete! Backend is running and ready to use."

# Run the backend services (Docker Compose)
run: 
	@echo "Starting backend services (Flask + Redis) with Docker Compose..."
	@docker-compose up -d --build # Build images if they don't exist and start in detached mode
	@echo "Backend services started. Flask API likely at http://localhost:5001"


# Backend daemon management
start-backend:
	@echo "Starting Magic Mirror backend daemon..."
	@pm2 start ecosystem.config.js
	@echo "Backend daemon started. Use 'make status-backend' to check status."

stop-backend:
	@echo "Stopping Magic Mirror backend daemon..."
	@pm2 stop $(BACKEND_APP_NAME)
	@echo "Backend daemon stopped."

restart-backend:
	@echo "Restarting Magic Mirror backend daemon..."
	@pm2 restart $(BACKEND_APP_NAME)
	@echo "Backend daemon restarted."

status-backend:
	@echo "Magic Mirror backend daemon status:"
	@pm2 status $(BACKEND_APP_NAME)

logs-backend:
	@echo "Magic Mirror backend daemon logs:"
	@pm2 logs $(BACKEND_APP_NAME) --lines 50

# Setup backend daemon to start on boot
setup-backend-daemon:
	@echo "Setting up Magic Mirror backend to start on boot..."
	@pm2 startup
	@pm2 save
	@echo "Backend daemon will now start automatically on boot."

# Run the main setup script (backend only)
setup:
	@echo "Running Magic Mirror Backend setup..."
	@./scripts/setup-backend.sh

# Setup systemd service for backend (requires sudo)
setup-systemd:
	@echo "Setting up systemd service for Magic Mirror backend..."
	@sudo ./scripts/setup-systemd.sh
	@echo "Systemd service installed and enabled."

# Clean up resources
clean:
	@echo "Stopping and removing backend containers and network..."
	@docker-compose down -v --remove-orphans # Stop, remove containers, network, and volumes
	@echo "Cleaning node_modules..."
	@rm -rf node_modules
	@echo "Cleanup complete." 

restart:
	@pm2 restart magic-mirror-backend
	@pm2 restart magicmirror
	@pm2 save
	@sudo reboot

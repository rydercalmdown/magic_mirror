# Makefile for Magic Mirror project

# Variables
# BACKEND_IMAGE_NAME = magic-mirror-backend # No longer needed directly
FRONTEND_DIR = frontend
# BACKEND_DIR = backend # No longer needed directly

.PHONY: install run frontend clean

# Install dependencies
install:
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && npm install
	# Backend dependencies are handled by docker-compose build
	@echo "Backend dependencies will be installed via docker-compose on first run."
	@echo "Installation complete."

# Run the backend services (Docker Compose)
run: 
	@echo "Starting backend services (Flask + Redis) with Docker Compose..."
	@docker-compose up -d --build # Build images if they don't exist and start in detached mode
	@echo "Backend services started. Flask API likely at http://localhost:5001"

# Run the frontend development server
frontend:
	@echo "Starting frontend development server..."
	cd $(FRONTEND_DIR) && npm run dev
	@echo "Frontend server accessible at http://localhost:3000 (usually)"

# Clean up Docker Compose resources
clean:
	@echo "Stopping and removing backend containers and network..."
	@docker-compose down -v --remove-orphans # Stop, remove containers, network, and volumes
	@echo "Cleaning frontend node_modules..."
	@rm -rf $(FRONTEND_DIR)/node_modules
	@rm -rf $(FRONTEND_DIR)/.next
	@echo "Cleanup complete." 
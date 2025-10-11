# Scripts Directory

This directory contains setup and utility scripts for the Magic Mirror project.

## Scripts

### `setup-backend.sh`
Main automated setup script that:
- Installs Node.js dependencies (express, cors)
- Installs PM2 globally if not present
- Creates logs directory
- Starts the backend with PM2
- Sets up PM2 to start on boot

**Usage:**
```bash
./scripts/setup-backend.sh
# or via Makefile: make setup
```

### `setup-systemd.sh`
Sets up a systemd service for the backend (alternative to PM2 startup).
Requires sudo privileges.

**Usage:**
```bash
sudo ./scripts/setup-systemd.sh
# or via Makefile: make setup-systemd
```

### `start-backend.sh`
Simple script to start the backend server directly (without PM2).
Useful for development or testing.

**Usage:**
```bash
./scripts/start-backend.sh
```

## Make Commands

For convenience, all scripts can be run via Makefile commands:

- `make setup` - Run main setup script
- `make setup-systemd` - Set up systemd service
- `make start-backend` - Start backend daemon
- `make stop-backend` - Stop backend daemon
- `make restart-backend` - Restart backend daemon
- `make status-backend` - Check backend status
- `make logs-backend` - View backend logs

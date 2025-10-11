# Magic Mirror - Habit Tracker
A MagicMirror module for tracking daily habits with completion status. Habits reset at the end of each day and can be toggled by clicking on them.

## Features

- 📅 Daily habit tracking with automatic reset
- ✅ Click to toggle habit completion status
- 🎯 Visual progress bar showing completion percentage
- 🎨 Modern, responsive design with strikethrough for completed habits
- 💾 Persistent data storage via backend API
- 🔄 Real-time updates

## Installation

1. Clone this repository or copy the `MMM-HabitTracker` folder to your MagicMirror modules directory:
   ```bash
   cd ~/MagicMirror/modules
   git clone https://github.com/rydercalmdown/magic_mirror.git MMM-HabitTracker
   ```

2. Install backend dependencies:
   ```bash
   cd MMM-HabitTracker
   npm install express cors
   ```

3. Add the module to your MagicMirror configuration in `config/config.js`:

   ```javascript
   {
       module: "MMM-HabitTracker",
       position: "top_right",
       config: {
           updateInterval: 2000, // Update every two seconds
           habits: [
               "Brush teeth",
               "Floss",
               "Exercise", 
               "Read for 30 minutes",
               "Meditate"
           ],
           backendUrl: "http://localhost:5000",
           showCompletedCount: true,
           showProgressBar: true
       }
   }
   ```

## Backend Setup

The module requires a simple backend API to store habit data. The backend can be run as a daemon using PM2 for automatic restart and management.

### Quick Setup

**One-command setup (recommended)**
```bash
make install
```
This will install all dependencies and set up the backend daemon.

**Manual setup**
```bash
# Install dependencies only
npm install express cors

# Setup backend daemon
make setup

# (Optional) Set up auto-start on boot
make setup-backend-daemon
```

### Backend Management Commands

| Command | Description |
|---------|-------------|
| `make install` | **Install all dependencies and setup backend** |
| `make setup` | Run the automated backend setup script |
| `make start-backend` | Start the backend daemon |
| `make stop-backend` | Stop the backend daemon |
| `make restart-backend` | Restart the backend daemon |
| `make status-backend` | Check backend status |
| `make logs-backend` | View backend logs |
| `make setup-backend-daemon` | Set up auto-start on boot |
| `make setup-systemd` | Set up systemd service (requires sudo) |

### Scripts Directory

All setup and utility scripts are located in the `scripts/` directory:

- `scripts/setup-backend.sh` - Main automated setup script (portable across systems)
- `scripts/setup-systemd.sh` - Systemd service setup (portable across systems)
- `scripts/start-backend.sh` - Simple backend startup script

**Note:** All scripts automatically detect their location and work on any system (macOS, Linux, Raspberry Pi, etc.).

The backend will run on `http://localhost:5000` by default.

### Backend API Endpoints

- `GET /api/habits?date=YYYY-MM-DD` - Get habits for a specific date
- `POST /api/habits` - Save habits for a specific date
- `GET /api/health` - Health check endpoint
- `GET /api/habits/all` - Get all habits data (for debugging)

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `updateInterval` | Number | 60000 | Update interval in milliseconds |
| `habits` | Array | `["Brush teeth", "Floss", "Exercise", "Read for 30 minutes", "Meditate"]` | List of habits to track |
| `backendUrl` | String | `"http://localhost:5000"` | Backend API URL |
| `showCompletedCount` | Boolean | `true` | Show completed count in progress bar |
| `showProgressBar` | Boolean | `true` | Show progress bar |

## Usage

1. **Install and setup**: `make install` (installs dependencies and starts backend)
2. Start your MagicMirror
3. Click on any habit to toggle its completion status
4. Habits automatically reset at the end of each day
5. Completed habits are displayed with strikethrough text

### Backend Management

- **Install and setup**: `make install`
- **Start backend**: `make start-backend`
- **Stop backend**: `make stop-backend`
- **Restart backend**: `make restart-backend`
- **Check status**: `make status-backend`
- **View logs**: `make logs-backend`
- **Auto-start on boot**: `make setup-backend-daemon`

## Project Structure

```
magic_mirror/
├── data/                   # Data storage directory
│   └── habits_data.json   # Habit tracking data
├── scripts/               # Setup and utility scripts
│   ├── setup-backend.sh
│   ├── setup-systemd.sh
│   └── start-backend.sh
├── logs/                  # PM2 log files
├── module.js              # MagicMirror module
├── MMM-HabitTracker.css   # Module styling
├── backend.js             # Backend API server
├── ecosystem.config.js    # PM2 configuration
└── Makefile              # Build and management commands
```

## Data Storage

Habit data is stored in `data/habits_data.json` in the project directory. The data structure is:

```json
{
  "2024-01-15": [
    {
      "name": "Brush teeth",
      "completed": true,
      "date": "2024-01-15"
    },
    {
      "name": "Floss", 
      "completed": false,
      "date": "2024-01-15"
    }
  ]
}
```

## Customization

### Adding New Habits

Edit the `habits` array in your MagicMirror config:

```javascript
habits: [
    "Brush teeth",
    "Floss",
    "Exercise",
    "Read for 30 minutes", 
    "Meditate",
    "Drink 8 glasses of water",
    "Take vitamins"
]
```

### Styling

The module uses `MMM-HabitTracker.css` for styling. You can customize colors, fonts, and layout by modifying this file.

## Troubleshooting

1. **Backend not responding**: Make sure the backend server is running on the correct port
2. **Habits not saving**: Check that the backend has write permissions to the module directory
3. **Module not loading**: Verify the module is properly installed in the MagicMirror modules directory

## Development

To modify the module:

1. Edit `module.js` for functionality changes
2. Edit `MMM-HabitTracker.css` for styling changes
3. Edit `backend.js` for API changes
4. Restart MagicMirror to see changes

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open an issue on the GitHub repository.

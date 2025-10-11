# MMM-HabitTracker

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
   git clone <repository-url> MMM-HabitTracker
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
           updateInterval: 60000, // Update every minute
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

The module requires a simple backend API to store habit data. Start the backend server:

```bash
cd MMM-HabitTracker
node backend.js
```

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

1. Start the backend server: `node backend.js`
2. Start your MagicMirror
3. Click on any habit to toggle its completion status
4. Habits automatically reset at the end of each day
5. Completed habits are displayed with strikethrough text

## Data Storage

Habit data is stored in `habits_data.json` in the module directory. The data structure is:

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

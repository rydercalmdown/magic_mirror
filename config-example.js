// Example MagicMirror configuration for MMM-HabitTracker
// Add this to your config/config.js file

{
    module: "MMM-HabitTracker",
    position: "center", // Center of the mirror
    config: {
        // Update interval in milliseconds (60000 = 1 minute)
        updateInterval: 60000,
        habits: [
            "Brush teeth",
            "Floss", 
            "Exercise",
            "Read for 30 minutes",
            "Meditate",
            "Drink 8 glasses of water",
            "Take vitamins",
            "Walk 10,000 steps"
        ],
        backendUrl: "http://localhost:5000",
        showCompletedCount: true,
        showProgressBar: true
    }
}


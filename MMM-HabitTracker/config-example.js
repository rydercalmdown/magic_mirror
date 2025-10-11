// Example MagicMirror configuration for MMM-HabitTracker
// Add this to your config/config.js file

{
    module: "MMM-HabitTracker",
    position: "top_right", // or "top_left", "bottom_right", "bottom_left", etc.
    config: {
        // Update interval in milliseconds (60000 = 1 minute)
        updateInterval: 60000,
        
        // List of habits to track
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
        
        // Backend API URL
        backendUrl: "http://localhost:5000",
        
        // Show completed count in progress bar
        showCompletedCount: true,
        
        // Show progress bar
        showProgressBar: true
    }
}

// Alternative configuration for different positions:
// {
//     module: "MMM-HabitTracker",
//     position: "top_left",
//     config: {
//         updateInterval: 30000, // Update every 30 seconds
//         habits: [
//             "Morning routine",
//             "Workout",
//             "Healthy meal",
//             "Learn something new"
//         ],
//         backendUrl: "http://localhost:5000",
//         showCompletedCount: true,
//         showProgressBar: true
//     }
// }

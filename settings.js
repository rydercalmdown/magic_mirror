// Backend settings for MMM-HabitTracker
// This file contains all the configuration for the habit tracker

module.exports = {
    // Backend server settings
    port: 5000,
    
    // Habit configuration
    habits: [
        "Brush teeth",
        "Floss",
    ],
    
    // Module settings
    module: {
        updateInterval: 60000, // Update every minute
        showCompletedCount: true,
        showProgressBar: true
    },
    
    // Data settings
    data: {
        file: "data/habits_data.json"
    }
};

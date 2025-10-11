Module.register("MMM-HabitTracker", {
    // Default module config
    defaults: {
        updateInterval: 60000, // Update every minute
        habits: [
            "Brush teeth",
            "Floss",
            "Exercise",
            "Read for 30 minutes",
            "Meditate"
        ],
        backendUrl: "http://localhost:5000", // Backend API URL
        showCompletedCount: true,
        showProgressBar: true
    },

    // Module properties
    habits: [],
    lastUpdateDate: null,

    // Start the module
    start: function() {
        Log.info("🚀 MMM-HabitTracker: Starting module");
        Log.info("📋 MMM-HabitTracker: Config - " + JSON.stringify(this.config));
        Log.info("🌐 MMM-HabitTracker: Backend URL - " + this.config.backendUrl);
        this.loadHabits();
        this.scheduleUpdate();
        Log.info("✅ MMM-HabitTracker: Module started successfully");
    },

    // Load habits from backend or initialize with defaults
    loadHabits: function() {
        const today = this.getTodayString();
        Log.info("📅 MMM-HabitTracker: Loading habits for date - " + today);
        
        // Check if we need to reset habits for a new day
        if (this.lastUpdateDate && this.lastUpdateDate !== today) {
            Log.info("🔄 MMM-HabitTracker: New day detected, resetting habits");
            this.resetHabitsForNewDay();
        }
        
        this.lastUpdateDate = today;
        
        // Try to load from backend first
        Log.info("🌐 MMM-HabitTracker: Requesting habits from backend - " + this.config.backendUrl + "/api/habits");
        this.sendSocketNotification("LOAD_HABITS", {
            url: this.config.backendUrl + "/api/habits",
            date: today
        });
    },

    // Reset habits for a new day
    resetHabitsForNewDay: function() {
        this.habits = this.config.habits.map(habit => ({
            name: habit,
            completed: false,
            date: this.getTodayString()
        }));
        this.saveHabits();
    },

    // Get today's date as string (YYYY-MM-DD)
    getTodayString: function() {
        const today = new Date();
        return today.getFullYear() + '-' + 
               String(today.getMonth() + 1).padStart(2, '0') + '-' + 
               String(today.getDate()).padStart(2, '0');
    },

    // Save habits to backend
    saveHabits: function() {
        this.sendSocketNotification("SAVE_HABITS", {
            url: this.config.backendUrl + "/api/habits",
            habits: this.habits,
            date: this.getTodayString()
        });
    },

    // Toggle habit completion status
    toggleHabit: function(habitName) {
        const habit = this.habits.find(h => h.name === habitName);
        if (habit) {
            const wasCompleted = habit.completed;
            habit.completed = !habit.completed;
            Log.info(`🔄 MMM-HabitTracker: Toggled habit "${habitName}" from ${wasCompleted} to ${habit.completed}`);
            this.saveHabits();
            this.updateDom();
        } else {
            Log.error("❌ MMM-HabitTracker: Could not find habit to toggle - " + habitName);
        }
    },

    // Schedule periodic updates
    scheduleUpdate: function() {
        setInterval(() => {
            this.loadHabits();
        }, this.config.updateInterval);
    },

    // Handle socket notifications
    socketNotificationReceived: function(notification, payload) {
        Log.info("📨 MMM-HabitTracker: Received notification - " + notification);
        
        if (notification === "HABITS_LOADED") {
            if (payload && payload.habits) {
                this.habits = payload.habits;
                Log.info("✅ MMM-HabitTracker: Loaded " + this.habits.length + " habits from backend");
                Log.info("📋 MMM-HabitTracker: Habits - " + JSON.stringify(this.habits.map(h => h.name)));
            } else {
                // Initialize with default habits if none loaded
                Log.warn("⚠️ MMM-HabitTracker: No habits from backend, using defaults");
                this.habits = this.config.habits.map(habit => ({
                    name: habit,
                    completed: false,
                    date: this.getTodayString()
                }));
            }
            this.updateDom();
        } else if (notification === "HABITS_SAVED") {
            Log.info("✅ MMM-HabitTracker: Habits saved successfully");
        } else if (notification === "HABITS_ERROR") {
            Log.error("❌ MMM-HabitTracker: Error loading/saving habits - " + JSON.stringify(payload));
            // Fallback to local storage or default habits
            Log.warn("🔄 MMM-HabitTracker: Falling back to default habits");
            this.habits = this.config.habits.map(habit => ({
                name: habit,
                completed: false,
                date: this.getTodayString()
            }));
            this.updateDom();
        }
    },

    // Get the DOM content
    getDom: function() {
        Log.info("🎨 MMM-HabitTracker: Rendering DOM with " + this.habits.length + " habits");
        const wrapper = document.createElement("div");
        wrapper.className = "habit-tracker";

        // Header
        const header = document.createElement("div");
        header.className = "habit-header";
        header.innerHTML = `
            <h1>Habits</h1>
            <h3>Today's Progress</h3>
        `;
        wrapper.appendChild(header);

        // Progress bar
        if (this.config.showProgressBar) {
            const completedCount = this.habits.filter(h => h.completed).length;
            const totalCount = this.habits.length;
            const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
            
            const progressBar = document.createElement("div");
            progressBar.className = "habit-progress";
            progressBar.innerHTML = `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <div class="progress-text">${completedCount}/${totalCount} completed</div>
            `;
            wrapper.appendChild(progressBar);
        }

        // Habits list
        const habitsList = document.createElement("div");
        habitsList.className = "habits-list";

        if (this.habits.length === 0) {
            // Show loading or default habits if none loaded
            const defaultHabits = this.config.habits || ["Loading habits..."];
            defaultHabits.forEach(habit => {
                const habitItem = document.createElement("div");
                habitItem.className = "habit-item";
                habitItem.innerHTML = `
                    <span class="habit-checkbox">○</span>
                    <span class="habit-name">${habit}</span>
                `;
                habitsList.appendChild(habitItem);
            });
        } else {
            this.habits.forEach(habit => {
                const habitItem = document.createElement("div");
                habitItem.className = `habit-item ${habit.completed ? 'completed' : ''}`;
                habitItem.innerHTML = `
                    <span class="habit-checkbox">${habit.completed ? '✓' : '○'}</span>
                    <span class="habit-name">${habit.name}</span>
                `;
                
                // Add click handler to toggle completion
                habitItem.addEventListener('click', () => {
                    this.toggleHabit(habit.name);
                });
                
                habitsList.appendChild(habitItem);
            });
        }

        wrapper.appendChild(habitsList);

        return wrapper;
    },

    // Get styles
    getStyles: function() {
        return ["MMM-HabitTracker.css"];
    },

    // Get scripts
    getScripts: function() {
        return [];
    }
});

Module.register("MMM-HabitTracker", {
    // Default module config
    defaults: {
        backendUrl: "http://localhost:5000" // Backend API URL
    },

    // Module properties
    habits: [],
    lastUpdateDate: null,
    settings: null,
    randomNumber: 0,
    personDetected: false,

    // Start the module
    start: function() {
        Log.info("🚀 MMM-HabitTracker: Starting module");
        Log.info("📋 MMM-HabitTracker: Config - " + JSON.stringify(this.config));
        Log.info("🌐 MMM-HabitTracker: Backend URL - " + this.config.backendUrl);
        
        // Initialize with empty habits
        this.habits = [];
        this.randomNumber = 0;
        
        // Tell node helper to initialize
        this.sendSocketNotification("INIT", {
            backendUrl: this.config.backendUrl
        });
        
        // Load settings and habits
        this.loadSettings();
        
        Log.info("✅ MMM-HabitTracker: Module started successfully");
    },

    // Handle socket notifications from node helper
    socketNotificationReceived: function(notification, payload) {
        Log.info("📨 MMM-HabitTracker: Received notification - " + notification);
        
        if (notification === "SETTINGS_LOADED") {
            if (payload && payload.habits) {
                this.settings = payload;
                Log.info("✅ MMM-HabitTracker: Settings loaded - " + payload.habits.length + " habits");
                this.loadHabits();
                this.scheduleUpdate();
            } else {
                Log.error("❌ MMM-HabitTracker: Failed to load settings - " + JSON.stringify(payload));
            }
        } else if (notification === "HABITS_LOADED") {
            if (payload && payload.habits) {
                this.habits = payload.habits;
                Log.info("✅ MMM-HabitTracker: Loaded " + this.habits.length + " habits from backend");
                Log.info("📋 MMM-HabitTracker: Habits - " + JSON.stringify(this.habits.map(h => h.name)));
            } else {
                Log.error("❌ MMM-HabitTracker: No habits from backend - " + JSON.stringify(payload));
            }
            this.updateDom();
        } else if (notification === "HABITS_SAVED") {
            Log.info("✅ MMM-HabitTracker: Habits saved successfully");
        } else if (notification === "HABITS_ERROR") {
            Log.error("❌ MMM-HabitTracker: Error loading/saving habits - " + JSON.stringify(payload));
        } else if (notification === "RANDOM_NUMBER") {
            this.randomNumber = payload.number;
            Log.info(`🧪 MMM-HabitTracker: Received random number: ${payload.number}`);
            this.updateDom();
        } else if (notification === "TEST_STATUS") {
            Log.info("🧪 MMM-HabitTracker: Test service status - " + JSON.stringify(payload));
        } else if (notification === "PERSON_DETECTION") {
            this.personDetected = payload.detected;
            Log.info(`👤 MMM-HabitTracker: Person ${payload.detected ? 'detected' : 'not detected'}`);
            this.updateDom();
        } else if (notification === "WEBCAM_STATUS") {
            Log.info("📹 MMM-HabitTracker: Webcam status - " + JSON.stringify(payload));
        } else if (notification === "WEBCAM_ERROR") {
            Log.error("❌ MMM-HabitTracker: Webcam error - " + JSON.stringify(payload));
        }
    },

    // Load settings from backend
    loadSettings: function() {
        Log.info("⚙️ MMM-HabitTracker: Loading settings from backend");
        this.sendSocketNotification("LOAD_SETTINGS", {
            url: this.config.backendUrl + "/api/settings"
        });
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
        
        // If we have settings, use them to initialize habits
        if (this.settings && this.settings.habits) {
            Log.info("📋 MMM-HabitTracker: Using settings habits - " + this.settings.habits.length + " habits");
            this.habits = this.settings.habits.map(habit => ({
                name: habit,
                completed: false,
                date: today
            }));
            this.updateDom();
        } else {
            // Try to load from backend
            Log.info("🌐 MMM-HabitTracker: Requesting habits from backend - " + this.config.backendUrl + "/api/habits");
            this.sendSocketNotification("LOAD_HABITS", {
                url: this.config.backendUrl + "/api/habits",
                date: today
            });
        }
    },

    // Reset habits for a new day
    resetHabitsForNewDay: function() {
        if (!this.settings || !this.settings.habits) {
            Log.error("❌ MMM-HabitTracker: Cannot reset habits - no settings available");
            return;
        }
        this.habits = this.settings.habits.map(habit => ({
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
        
        if (notification === "SETTINGS_LOADED") {
            if (payload && payload.habits) {
                this.settings = payload;
                Log.info("✅ MMM-HabitTracker: Settings loaded - " + payload.habits.length + " habits");
                this.loadHabits();
                this.scheduleUpdate();
            } else {
                Log.error("❌ MMM-HabitTracker: Failed to load settings");
            }
        } else if (notification === "HABITS_LOADED") {
            if (payload && payload.habits) {
                this.habits = payload.habits;
                Log.info("✅ MMM-HabitTracker: Loaded " + this.habits.length + " habits from backend");
                Log.info("📋 MMM-HabitTracker: Habits - " + JSON.stringify(this.habits.map(h => h.name)));
            } else {
                Log.error("❌ MMM-HabitTracker: No habits from backend - " + JSON.stringify(payload));
            }
            this.updateDom();
        } else if (notification === "HABITS_SAVED") {
            Log.info("✅ MMM-HabitTracker: Habits saved successfully");
        } else if (notification === "HABITS_ERROR") {
            Log.error("❌ MMM-HabitTracker: Error loading/saving habits - " + JSON.stringify(payload));
        } else if (notification === "RANDOM_NUMBER") {
            this.randomNumber = payload.number;
            Log.info(`🧪 MMM-HabitTracker: Received random number: ${payload.number}`);
            this.updateDom();
        } else if (notification === "TEST_STATUS") {
            Log.info("🧪 MMM-HabitTracker: Test service status - " + JSON.stringify(payload));
        } else if (notification === "PERSON_DETECTION") {
            this.personDetected = payload.detected;
            Log.info(`👤 MMM-HabitTracker: Person ${payload.detected ? 'detected' : 'not detected'}`);
            this.updateDom();
        } else if (notification === "WEBCAM_STATUS") {
            Log.info("📹 MMM-HabitTracker: Webcam status - " + JSON.stringify(payload));
        } else if (notification === "WEBCAM_ERROR") {
            Log.error("❌ MMM-HabitTracker: Webcam error - " + JSON.stringify(payload));
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
        header.innerHTML = `<h2>Daily Habits</h2>`;
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
            const defaultHabits = this.settings ? this.settings.habits : ["Loading habits..."];
            defaultHabits.forEach((habit, index) => {
                const habitItem = document.createElement("div");
                habitItem.className = "habit-item";
                habitItem.innerHTML = `<div class="habit-text">${habit}</div>`;
                habitsList.appendChild(habitItem);
                
                // Add HR between habits (not after the last one)
                if (index < defaultHabits.length - 1) {
                    const hr = document.createElement("hr");
                    hr.className = "habit-separator";
                    habitsList.appendChild(hr);
                }
            });
        } else {
            this.habits.forEach((habit, index) => {
                const habitItem = document.createElement("div");
                habitItem.className = `habit-item ${habit.completed ? 'completed' : ''}`;
                habitItem.innerHTML = `<div class="habit-text">${habit.name}</div>`;
                
                // Add click handler to toggle completion
                habitItem.addEventListener('click', () => {
                    this.toggleHabit(habit.name);
                });
                
                habitsList.appendChild(habitItem);
                
                // Add HR between habits (not after the last one)
                if (index < this.habits.length - 1) {
                    const hr = document.createElement("hr");
                    hr.className = "habit-separator";
                    habitsList.appendChild(hr);
                }
            });
        }

        wrapper.appendChild(habitsList);

        // Random number display
        const numberDiv = document.createElement("div");
        numberDiv.className = "random-number";
        numberDiv.innerHTML = `
            <div class="number-label">Test Number:</div>
            <div class="number-value">${this.randomNumber}</div>
        `;
        wrapper.appendChild(numberDiv);

        // Person detection status
        const personDiv = document.createElement("div");
        personDiv.className = "person-status";
        personDiv.innerHTML = `
            <div class="status-indicator ${this.personDetected ? 'detected' : 'not-detected'}"></div>
            <div class="status-text">${this.personDetected ? 'Person detected' : 'Person not detected'}</div>
        `;
        wrapper.appendChild(personDiv);

        // Live webcam preview via MJPEG stream
        const streamUrl = this.config.backendUrl.replace(/\/$/, '') + "/stream";
        const img = document.createElement('img');
        img.src = streamUrl;
        img.alt = 'Webcam stream';
        img.style.display = 'block';
        img.style.marginTop = '10px';
        img.style.maxWidth = '100%';
        img.style.borderRadius = '8px';
        img.style.opacity = '0.9';
        wrapper.appendChild(img);

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

// Node helper for MMM-HabitTracker
// Handles socket notifications and backend communication

const NodeHelper = require("node_helper");
const https = require("https");
const http = require("http");

module.exports = NodeHelper.create({
    start: function() {
        console.log("🚀 MMM-HabitTracker: Node helper started");
    },

    socketNotificationReceived: function(notification, payload) {
        console.log("📨 MMM-HabitTracker: Received notification - " + notification);
        
        if (notification === "LOAD_SETTINGS") {
            this.loadSettings(payload.url);
        } else if (notification === "LOAD_HABITS") {
            this.loadHabits(payload.url, payload.date);
        } else if (notification === "SAVE_HABITS") {
            this.saveHabits(payload.url, payload.habits, payload.date);
        }
    },

    loadSettings: function(url) {
        console.log("⚙️ MMM-HabitTracker: Loading settings from " + url);
        this.makeRequest(url, (data) => {
            this.sendSocketNotification("SETTINGS_LOADED", data);
        });
    },

    loadHabits: function(url, date) {
        console.log("📅 MMM-HabitTracker: Loading habits from " + url + " for date " + date);
        const fullUrl = url + "?date=" + date;
        this.makeRequest(fullUrl, (data) => {
            this.sendSocketNotification("HABITS_LOADED", data);
        });
    },

    saveHabits: function(url, habits, date) {
        console.log("💾 MMM-HabitTracker: Saving habits to " + url);
        this.makeRequest(url, (data) => {
            this.sendSocketNotification("HABITS_SAVED", data);
        }, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ habits, date })
        });
    },

    makeRequest: function(url, callback, options = {}) {
        const isHttps = url.startsWith("https://");
        const client = isHttps ? https : http;
        
        const requestOptions = {
            method: options.method || "GET",
            headers: options.headers || {}
        };

        const req = client.request(url, requestOptions, (res) => {
            let data = "";
            
            res.on("data", (chunk) => {
                data += chunk;
            });
            
            res.on("end", () => {
                try {
                    const jsonData = JSON.parse(data);
                    callback(jsonData);
                } catch (error) {
                    console.error("❌ MMM-HabitTracker: Error parsing response - " + error.message);
                    this.sendSocketNotification("HABITS_ERROR", { error: error.message });
                }
            });
        });

        req.on("error", (error) => {
            console.error("❌ MMM-HabitTracker: Request error - " + error.message);
            this.sendSocketNotification("HABITS_ERROR", { error: error.message });
        });

        if (options.body) {
            req.write(options.body);
        }
        
        req.end();
    }
});

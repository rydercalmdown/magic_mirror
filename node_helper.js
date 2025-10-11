// Node helper for MMM-HabitTracker
// Handles backend communication via WebSocket and HTTP

const NodeHelper = require("node_helper");
const https = require("https");
const http = require("http");
const io = require("socket.io-client");

module.exports = NodeHelper.create({
    start: function() {
        console.log("🚀 MMM-HabitTracker: Node helper started");
        this.backendSocket = null;
        this.backendUrl = null;
    },

    socketNotificationReceived: function(notification, payload) {
        console.log("📨 MMM-HabitTracker: Received notification - " + notification);
        
        if (notification === "INIT") {
            this.backendUrl = payload.backendUrl;
            this.connectToBackend();
        } else if (notification === "LOAD_SETTINGS") {
            this.loadSettings(payload.url);
        } else if (notification === "LOAD_HABITS") {
            this.loadHabits(payload.url, payload.date);
        } else if (notification === "SAVE_HABITS") {
            this.saveHabits(payload.url, payload.habits, payload.date);
        }
    },

    connectToBackend: function() {
        if (!this.backendUrl) {
            console.error("❌ MMM-HabitTracker: No backend URL provided");
            return;
        }

        console.log("🔌 MMM-HabitTracker: Connecting to backend at " + this.backendUrl);
        
        this.backendSocket = io(this.backendUrl, {
            transports: ['websocket'],
            upgrade: false,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: Infinity,
            timeout: 30000,
            perMessageDeflate: false
        });

        this.backendSocket.on('connect', () => {
            console.log("✅ MMM-HabitTracker: Connected to backend");
            console.log("🔌 MMM-HabitTracker: Socket ID:", this.backendSocket.id);
            this.sendSocketNotification("TEST_STATUS", { connected: true });
        });

        this.backendSocket.on('disconnect', () => {
            console.log("❌ MMM-HabitTracker: Disconnected from backend");
            this.sendSocketNotification("TEST_STATUS", { connected: false });
        });

        this.backendSocket.on('randomNumber', (data) => {
            console.log("🧪 MMM-HabitTracker: Received random number from backend: " + data.number);
            this.sendSocketNotification("RANDOM_NUMBER", data);
        });

        // Add debugging for all events
        this.backendSocket.onAny((eventName, ...args) => {
            console.log("🔍 MMM-HabitTracker: Received event:", eventName, "with data:", args);
        });

        this.backendSocket.on('testStatus', (status) => {
            console.log("🧪 MMM-HabitTracker: Backend test status: " + JSON.stringify(status));
            this.sendSocketNotification("TEST_STATUS", status);
        });

        this.backendSocket.on('personDetection', (data) => {
            console.log("👤 MMM-HabitTracker: Person detection from backend: " + data.detected);
            this.sendSocketNotification("PERSON_DETECTION", data);
        });

        this.backendSocket.on('webcamStatus', (status) => {
            console.log("📹 MMM-HabitTracker: Backend webcam status: " + JSON.stringify(status));
            this.sendSocketNotification("WEBCAM_STATUS", status);
        });

        this.backendSocket.on('webcamError', (error) => {
            console.error("❌ MMM-HabitTracker: Backend webcam error: " + error.message);
            this.sendSocketNotification("WEBCAM_ERROR", error);
        });

        // Action recognition events
        this.backendSocket.on('currentAction', (data) => {
            console.log("🤖 MMM-HabitTracker: Current action from backend: " + JSON.stringify(data));
            this.sendSocketNotification("CURRENT_ACTION", data);
        });

        this.backendSocket.on('habitUpdated', (data) => {
            console.log("✅ MMM-HabitTracker: Habits updated from backend action: " + JSON.stringify(data));
            this.sendSocketNotification("HABITS_UPDATED", data);
        });

        this.backendSocket.on('connect_error', (error) => {
            console.error("❌ MMM-HabitTracker: Backend connection error: " + error.message);
            this.sendSocketNotification("TEST_STATUS", { connected: false, error: error.message });
        });
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

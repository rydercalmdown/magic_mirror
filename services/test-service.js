// Test service for WebSocket communication
// Sends random numbers to frontend every 1-5 seconds

const EventEmitter = require('events');

class TestService extends EventEmitter {
    constructor(options = {}) {
        super();
        this.isRunning = false;
        this.intervalId = null;
        this.minInterval = options.minInterval || 1000; // 1 second
        this.maxInterval = options.maxInterval || 5000; // 5 seconds
    }

    start() {
        if (this.isRunning) {
            console.log("⚠️ Test Service: Already running");
            return;
        }

        this.isRunning = true;
        this.scheduleNext();
        console.log("🧪 Test Service: Started sending random numbers");
        this.emit('started');
    }

    stop() {
        if (!this.isRunning) {
            console.log("⚠️ Test Service: Not running");
            return;
        }

        this.isRunning = false;
        
        if (this.intervalId) {
            clearTimeout(this.intervalId);
            this.intervalId = null;
        }

        console.log("🛑 Test Service: Stopped");
        this.emit('stopped');
    }

    scheduleNext() {
        if (!this.isRunning) return;

        // Generate random interval between min and max
        const interval = Math.random() * (this.maxInterval - this.minInterval) + this.minInterval;
        
        this.intervalId = setTimeout(() => {
            this.sendRandomNumber();
            this.scheduleNext(); // Schedule the next one
        }, interval);
    }

    sendRandomNumber() {
        // Generate random 2-digit number (10-99)
        const randomNumber = Math.floor(Math.random() * 90) + 10;
        
        console.log(`🧪 Test Service: Sending random number: ${randomNumber}`);
        
        this.emit('randomNumber', {
            number: randomNumber,
            timestamp: new Date().toISOString()
        });
    }

    getStatus() {
        return {
            isRunning: this.isRunning,
            minInterval: this.minInterval,
            maxInterval: this.maxInterval
        };
    }
}

module.exports = TestService;

// Backend for habit tracking and webcam monitoring
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const http = require('http');
const socketIo = require('socket.io');
const settings = require('./settings');
const TestService = require('./services/test-service');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

const PORT = process.env.PORT || settings.port;

// Middleware
app.use(cors());
app.use(express.json());

// Data storage file
const DATA_FILE = path.join(__dirname, settings.data.file);
const DATA_DIR = path.dirname(DATA_FILE);

// Create data directory if it doesn't exist
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Initialize data file if it doesn't exist
if (!fs.existsSync(DATA_FILE)) {
    fs.writeFileSync(DATA_FILE, JSON.stringify({}));
}

// Initialize test service
const testService = new TestService({
    minInterval: 1000, // 1 second
    maxInterval: 5000  // 5 seconds
});

// WebSocket connection handling
io.on('connection', (socket) => {
    console.log('🔌 Client connected:', socket.id);
    
    // Send current test service status
    socket.emit('testStatus', testService.getStatus());
    
    socket.on('disconnect', () => {
        console.log('🔌 Client disconnected:', socket.id);
    });
});

// Test service event handlers
testService.on('randomNumber', (data) => {
    console.log(`🧪 Test Service: Sending random number ${data.number} to frontend`);
    io.emit('randomNumber', data);
});

testService.on('started', () => {
    console.log('✅ Test Service started successfully');
    io.emit('testStatus', testService.getStatus());
});

testService.on('stopped', () => {
    console.log('🛑 Test Service stopped');
    io.emit('testStatus', testService.getStatus());
});

// Load habits data
function loadHabitsData() {
    try {
        const data = fs.readFileSync(DATA_FILE, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error('Error loading habits data:', error);
        return {};
    }
}

// Save habits data
function saveHabitsData(data) {
    try {
        fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
        return true;
    } catch (error) {
        console.error('Error saving habits data:', error);
        return false;
    }
}

// Get habits for a specific date
app.get('/api/habits', (req, res) => {
    const { date } = req.query;
    const targetDate = date || new Date().toISOString().split('T')[0];
    
    const habitsData = loadHabitsData();
    const dayHabits = habitsData[targetDate] || [];
    
    res.json({
        date: targetDate,
        habits: dayHabits
    });
});

// Save habits for a specific date
app.post('/api/habits', (req, res) => {
    const { date, habits } = req.body;
    const targetDate = date || new Date().toISOString().split('T')[0];
    
    if (!habits || !Array.isArray(habits)) {
        return res.status(400).json({ error: 'Invalid habits data' });
    }
    
    const habitsData = loadHabitsData();
    habitsData[targetDate] = habits;
    
    if (saveHabitsData(habitsData)) {
        res.json({ 
            success: true, 
            message: 'Habits saved successfully',
            date: targetDate,
            habits: habits
        });
    } else {
        res.status(500).json({ error: 'Failed to save habits' });
    }
});

// Get all habits data (for debugging)
app.get('/api/habits/all', (req, res) => {
    const habitsData = loadHabitsData();
    res.json(habitsData);
});

// Get settings endpoint
app.get('/api/settings', (req, res) => {
    res.json({
        habits: settings.habits,
        module: settings.module
    });
});

// Test service control endpoints
app.post('/api/test/start', (req, res) => {
    testService.start();
    res.json({ success: true, message: 'Test service started' });
});

app.post('/api/test/stop', (req, res) => {
    testService.stop();
    res.json({ success: true, message: 'Test service stopped' });
});

app.get('/api/test/status', (req, res) => {
    res.json(testService.getStatus());
});

// Health check endpoint
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        test: testService.getStatus()
    });
});

// Start server
server.listen(PORT, () => {
    console.log(`🚀 Habit Tracker Backend running on port ${PORT}`);
    console.log(`🌐 Health check: http://localhost:${PORT}/api/health`);
    console.log(`📋 Habits API: http://localhost:${PORT}/api/habits`);
    console.log(`🧪 Test API: http://localhost:${PORT}/api/test/status`);
    console.log(`🔌 WebSocket: ws://localhost:${PORT}`);
    
    // Start test service automatically
    console.log(`🧪 Starting test service...`);
    testService.start();
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down gracefully...');
    testService.stop();
    server.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
    });
});

module.exports = { app, server, testService };

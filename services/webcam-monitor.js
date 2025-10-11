// Webcam monitoring service for person detection
// This service runs continuously and detects people in front of the camera

const cv = require('opencv4nodejs');
const EventEmitter = require('events');

class WebcamMonitor extends EventEmitter {
    constructor(options = {}) {
        super();
        this.cameraIndex = options.cameraIndex || 0;
        this.detectionInterval = options.detectionInterval || 1000; // Check every 1 second
        this.isRunning = false;
        this.cap = null;
        this.intervalId = null;
        
        // Person detection state
        this.personDetected = false;
        this.lastDetectionTime = null;
        
        // Load Haar cascade for person detection
        this.faceCascade = null;
        this.bodyCascade = null;
        this.loadCascades();
    }

    async loadCascades() {
        try {
            // Load Haar cascades for face and body detection
            this.faceCascade = new cv.CascadeClassifier(cv.HAAR_FRONTALFACE_ALT2);
            this.bodyCascade = new cv.CascadeClassifier(cv.HAAR_FULLBODY);
            console.log("✅ Webcam Monitor: Cascades loaded successfully");
        } catch (error) {
            console.error("❌ Webcam Monitor: Error loading cascades:", error.message);
            // Fallback to basic motion detection if cascades fail
            this.useMotionDetection = true;
        }
    }

    async start() {
        if (this.isRunning) {
            console.log("⚠️ Webcam Monitor: Already running");
            return;
        }

        try {
            // Initialize camera
            this.cap = new cv.VideoCapture(this.cameraIndex);
            
            // Set camera properties for better performance
            this.cap.set(cv.CAP_PROP_FRAME_WIDTH, 640);
            this.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480);
            this.cap.set(cv.CAP_PROP_FPS, 15);
            
            console.log("📹 Webcam Monitor: Camera initialized");
            
            this.isRunning = true;
            this.startDetection();
            
            console.log("🚀 Webcam Monitor: Started monitoring");
            this.emit('started');
            
        } catch (error) {
            console.error("❌ Webcam Monitor: Failed to start:", error.message);
            this.emit('error', error);
        }
    }

    startDetection() {
        this.intervalId = setInterval(async () => {
            try {
                await this.detectPerson();
            } catch (error) {
                console.error("❌ Webcam Monitor: Detection error:", error.message);
            }
        }, this.detectionInterval);
    }

    async detectPerson() {
        if (!this.cap || !this.isRunning) return;

        try {
            // Capture frame
            const frame = this.cap.read();
            if (frame.empty) {
                console.log("⚠️ Webcam Monitor: Empty frame received");
                return;
            }

            // Convert to grayscale for better performance
            const gray = frame.cvtColor(cv.COLOR_BGR2GRAY);
            
            let personFound = false;

            if (this.useMotionDetection) {
                // Fallback: Simple motion detection
                personFound = await this.detectMotion(gray);
            } else {
                // Primary: Face and body detection
                personFound = await this.detectFaceOrBody(gray);
            }

            // Update detection state
            const wasDetected = this.personDetected;
            this.personDetected = personFound;
            
            if (personFound) {
                this.lastDetectionTime = new Date();
            }

            // Emit event if detection state changed
            if (wasDetected !== this.personDetected) {
                this.emit('detectionChange', {
                    detected: this.personDetected,
                    timestamp: this.lastDetectionTime
                });
                console.log(`👤 Webcam Monitor: Person ${this.personDetected ? 'detected' : 'not detected'}`);
            }

        } catch (error) {
            console.error("❌ Webcam Monitor: Detection failed:", error.message);
        }
    }

    async detectFaceOrBody(gray) {
        try {
            // Detect faces
            const faces = this.faceCascade.detectMultiScale(gray, 1.1, 3, 0);
            if (faces.length > 0) {
                return true;
            }

            // Detect bodies
            const bodies = this.bodyCascade.detectMultiScale(gray, 1.1, 3, 0);
            if (bodies.length > 0) {
                return true;
            }

            return false;
        } catch (error) {
            console.error("❌ Webcam Monitor: Face/body detection error:", error.message);
            return false;
        }
    }

    async detectMotion(gray) {
        // Simple motion detection using frame differencing
        if (!this.previousFrame) {
            this.previousFrame = gray.copy();
            return false;
        }

        // Calculate absolute difference
        const diff = this.previousFrame.absdiff(gray);
        
        // Threshold the difference
        const thresh = diff.threshold(30, 255, cv.THRESH_BINARY);
        
        // Count non-zero pixels (motion)
        const motionPixels = thresh.countNonZero();
        
        // Update previous frame
        this.previousFrame = gray.copy();
        
        // Consider motion if more than 1000 pixels changed
        return motionPixels > 1000;
    }

    stop() {
        if (!this.isRunning) {
            console.log("⚠️ Webcam Monitor: Not running");
            return;
        }

        this.isRunning = false;
        
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        if (this.cap) {
            this.cap.release();
            this.cap = null;
        }

        console.log("🛑 Webcam Monitor: Stopped");
        this.emit('stopped');
    }

    getStatus() {
        return {
            isRunning: this.isRunning,
            personDetected: this.personDetected,
            lastDetectionTime: this.lastDetectionTime,
            cameraIndex: this.cameraIndex
        };
    }
}

module.exports = WebcamMonitor;

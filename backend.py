#!/usr/bin/env python3
"""
Backend for habit tracking and webcam monitoring
Python backend with OpenCV for person detection
"""

import json
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import socketio

# Ensure compatible async networking for Socket.IO (WebSocket support)
try:
    import eventlet
    import eventlet.wsgi
    eventlet.monkey_patch()
except Exception as _e:
    # If eventlet is not available, the server will fall back later
    pass

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize Socket.IO
sio = socketio.Server(
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    async_mode='eventlet',
    ping_interval=25,
    ping_timeout=60
)
flask_app = socketio.WSGIApp(sio, app)

# Configuration
PORT = int(os.environ.get('PORT', 5000))
DATA_FILE = Path(__file__).parent / 'data' / 'habits_data.json'

# Ensure data directory exists
DATA_FILE.parent.mkdir(exist_ok=True)

# Initialize data file if it doesn't exist
if not DATA_FILE.exists():
    DATA_FILE.write_text('{}')

# Load settings from JSON file
def load_settings():
    settings_file = Path(__file__).parent / 'settings.json'
    try:
        with open(settings_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Could not load settings.json: {e}")
        print("Using default settings...")
        return {
            'port': 5000,
            'data': {'file': 'data/habits_data.json'},
            'habits': ['Brush teeth', 'Floss'],
            'module': {
                'updateInterval': 60000,
                'showCompletedCount': True,
                'showProgressBar': True
            }
        }

settings = load_settings()

class ActionRecognizer:
    """Action recognition service that consumes webcam frames when a person is detected,
    estimates the current action, and marks habits complete after sustained detection.
    """
    def __init__(self, models_dir: Path, sustained_seconds: float = 60.0):
        self.models_dir = models_dir
        self.sustained_seconds = sustained_seconds
        self.enabled = True
        self.current_action = None
        self.last_action = None
        self.action_start_time = None
        self.last_emit_time = 0.0
        self.emit_interval = 0.5  # seconds between CURRENT_ACTION emits
        # Try to import pipeline from training
        self.pipeline = None
        try:
            # Lazy import to avoid heavy deps if missing
            sys.path.append(str((Path(__file__).parent / 'training').resolve()))
            from realtime_inference import RealtimeInference  # type: ignore
            self.pipeline = RealtimeInference(models_path=str(models_dir))
            print("🤖 ActionRecognizer: Loaded training pipeline")
        except Exception as e:
            print(f"⚠️ ActionRecognizer: Could not load training pipeline: {e}")
            self.enabled = False

    def process_frame(self, frame_bgr):
        if not self.enabled or self.pipeline is None:
            return
        try:
            # Pipeline is expected to return an action label or None
            action_label = self.pipeline.predict_frame_bgr(frame_bgr)
        except Exception as e:
            # If the pipeline raises, disable to avoid spamming
            print(f"⚠️ ActionRecognizer: Pipeline error: {e}")
            self.enabled = False
            return

        now = time.monotonic()

        # Emit current action periodically for the frontend
        if action_label != self.current_action or (now - self.last_emit_time) >= self.emit_interval:
            self.current_action = action_label
            self.last_emit_time = now
            sio.emit('currentAction', {
                'label': self.current_action
            })

        # Track sustained action window
        if action_label and action_label == self.last_action:
            # continue current streak
            pass
        else:
            # reset streak
            self.action_start_time = now if action_label else None
            self.last_action = action_label

        if self.action_start_time and action_label:
            elapsed = now - self.action_start_time
            if elapsed >= self.sustained_seconds:
                # Mark habit complete for matching action name if exists
                habit_name = self._map_action_to_habit(action_label)
                if habit_name:
                    try:
                        updated = mark_habit_completed(habit_name)
                        if updated:
                            sio.emit('habitUpdated', {
                                'habits': updated,
                                'completed': habit_name
                            })
                    except Exception as e:
                        print(f"❌ ActionRecognizer: Failed to mark habit complete: {e}")
                # reset timer to prevent repeated triggers
                self.action_start_time = now

    def _map_action_to_habit(self, action_label: str):
        # Simple mapping; adjust as needed to match your labels and habit names
        label = action_label.lower()
        if 'brush' in label:
            return 'Brush teeth'
        if 'floss' in label:
            return 'Floss'
        return None

class TestService:
    """Test service that sends random numbers"""
    
    def __init__(self, min_interval=1, max_interval=5):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.is_running = False
        self.thread = None
    
    def start(self):
        if self.is_running:
            print("⚠️ Test Service: Already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print("🧪 Test Service: Started sending random numbers")
    
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
        print("🛑 Test Service: Stopped")
    
    def _run(self):
        while self.is_running:
            import random
            number = random.randint(10, 99)
            print(f"🧪 Test Service: Sending random number {number} to frontend")
            sio.emit('randomNumber', {'number': number, 'timestamp': datetime.now().isoformat()})
            
            # Random interval between min and max
            interval = random.uniform(self.min_interval, self.max_interval)
            time.sleep(interval)
    
    def get_status(self):
        return {
            'isRunning': self.is_running,
            'minInterval': self.min_interval,
            'maxInterval': self.max_interval
        }

class WebcamMonitor:
    """Webcam monitoring service for person detection"""
    
    def __init__(self, camera_index=0, detection_interval=0.33, action_recognizer=None):
        self.camera_index = camera_index
        self.detection_interval = detection_interval
        self.is_running = False
        self.thread = None
        self.person_detected = False
        self.last_detection_time = None
        self.last_seen_time = None  # last frame timestamp where a person was seen
        self.latest_jpeg = None  # last encoded JPEG frame bytes for streaming
        self.action_recognizer = action_recognizer
        
        # Load Haar cascades
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
        
        if self.face_cascade.empty() or self.body_cascade.empty():
            print("⚠️ Webcam Monitor: Could not load Haar cascades, using motion detection")
            self.use_motion_detection = True
        else:
            print("✅ Webcam Monitor: Haar cascades loaded successfully")
            self.use_motion_detection = False
    
    def start(self):
        if self.is_running:
            print("⚠️ Webcam Monitor: Already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print("📹 Webcam Monitor: Started monitoring")
    
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
        print("🛑 Webcam Monitor: Stopped")
    
    def _run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"❌ Webcam Monitor: Could not open camera {self.camera_index}")
            return
        
        # Set camera properties (aim for native or higher FPS if available)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        previous_frame = None
        
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Webcam Monitor: Could not read frame")
                time.sleep(1)
                continue
            
            # Encode and store latest JPEG for the stream (lower quality to reduce latency)
            try:
                ok, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 55])
                if ok:
                    self.latest_jpeg = jpg.tobytes()
            except Exception as _:
                pass

            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            person_found = False
            
            if self.use_motion_detection:
                # Motion detection fallback
                person_found = self._detect_motion(gray, previous_frame)
            else:
                # Face and body detection
                person_found = self._detect_face_or_body(gray)
            
            # Smoothing/robustness: immediate detect, 2s grace before not-detected
            now_dt = datetime.now()
            was_detected = self.person_detected

            if person_found:
                self.last_seen_time = now_dt
                if not self.person_detected:
                    # switch to detected immediately
                    self.person_detected = True
                    self.last_detection_time = now_dt
                    print("👤 Person detection: DETECTED")
                    sio.emit('personDetection', {
                        'detected': True,
                        'timestamp': self.last_detection_time.isoformat()
                    })
                else:
                    # already detected; refresh timestamps
                    self.last_detection_time = now_dt
            else:
                # no person in this frame; only flip to not detected if >3s since last_seen
                if self.person_detected and self.last_seen_time is not None:
                    delta = (now_dt - self.last_seen_time).total_seconds()
                    if delta > 3.0:
                        self.person_detected = False
                        print("👤 Person detection: NOT DETECTED")
                        sio.emit('personDetection', {
                            'detected': False,
                            'timestamp': self.last_detection_time.isoformat() if self.last_detection_time else None
                        })
            
            previous_frame = gray.copy()
            time.sleep(self.detection_interval)

            # Feed frames to action recognizer only while a person is detected
            if self.person_detected and self.action_recognizer is not None:
                try:
                    self.action_recognizer.process_frame(frame)
                except Exception as _:
                    pass
        
        cap.release()
    
    def _detect_face_or_body(self, gray):
        """Detect faces or bodies using Haar cascades"""
        try:
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 3, 0)
            if len(faces) > 0:
                return True
            
            # Detect bodies
            bodies = self.body_cascade.detectMultiScale(gray, 1.1, 3, 0)
            if len(bodies) > 0:
                return True
            
            return False
        except Exception as e:
            print(f"❌ Webcam Monitor: Detection error: {e}")
            return False
    
    def _detect_motion(self, gray, previous_frame):
        """Simple motion detection using frame differencing"""
        if previous_frame is None:
            return False
        
        # Calculate absolute difference
        diff = cv2.absdiff(previous_frame, gray)
        
        # Threshold the difference
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # Count non-zero pixels (motion)
        motion_pixels = cv2.countNonZero(thresh)
        
        # Consider motion if more than 1000 pixels changed
        return motion_pixels > 1000
    
    def get_status(self):
        return {
            'isRunning': self.is_running,
            'personDetected': self.person_detected,
            'lastDetectionTime': self.last_detection_time.isoformat() if self.last_detection_time else None,
            'cameraIndex': self.camera_index
        }

# Initialize services
test_service = TestService(min_interval=1, max_interval=5)
action_recognizer = ActionRecognizer(models_dir=Path(__file__).parent / 'training' / 'models', sustained_seconds=60.0)
webcam_monitor = WebcamMonitor(camera_index=0, detection_interval=0.33, action_recognizer=action_recognizer)

# Socket.IO event handlers
@sio.event
def connect(sid, environ):
    print(f'🔌 Client connected: {sid}')
    sio.emit('testStatus', test_service.get_status())
    sio.emit('webcamStatus', webcam_monitor.get_status())
    # Emit an initial random number to update UI immediately
    try:
        import random
        initial = random.randint(10, 99)
        sio.emit('randomNumber', {'number': initial, 'timestamp': datetime.now().isoformat()}, room=sid)
    except Exception as e:
        print(f"⚠️ Could not emit initial random number: {e}")

@sio.event
def disconnect(sid):
    print(f'🔌 Client disconnected: {sid}')

# API Routes
@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'test': test_service.get_status(),
        'webcam': webcam_monitor.get_status()
    })

@app.route('/api/settings')
def get_settings():
    return jsonify({
        'habits': settings['habits'],
        'module': settings['module']
    })

@app.route('/api/habits')
def get_habits():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        if date in data:
            return jsonify({'habits': data[date]})
        else:
            # Initialize with settings habits
            habits = [{'name': habit, 'completed': False, 'date': date} for habit in settings['habits']]
            data[date] = habits
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return jsonify({'habits': habits})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def mark_habit_completed(habit_name: str):
    """Mark a habit complete for today and return updated habits list, or None on failure."""
    date = datetime.now().strftime('%Y-%m-%d')
    with open(DATA_FILE, 'r') as f:
        try:
            all_data = json.load(f)
        except json.JSONDecodeError:
            all_data = {}
    if date not in all_data:
        all_data[date] = [{'name': h, 'completed': False, 'date': date} for h in settings['habits']]
    updated = False
    for h in all_data[date]:
        if h.get('name') == habit_name:
            if not h.get('completed'):
                h['completed'] = True
                updated = True
            break
    with open(DATA_FILE, 'w') as f:
        json.dump(all_data, f, indent=2)
    return all_data[date] if updated else None

@app.route('/api/habits', methods=['POST'])
def save_habits():
    data = request.get_json()
    habits = data.get('habits', [])
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        with open(DATA_FILE, 'r') as f:
            all_data = json.load(f)
        
        all_data[date] = habits
        
        with open(DATA_FILE, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/start', methods=['POST'])
def start_test():
    test_service.start()
    return jsonify({'success': True, 'message': 'Test service started'})

@app.route('/api/test/stop', methods=['POST'])
def stop_test():
    test_service.stop()
    return jsonify({'success': True, 'message': 'Test service stopped'})

@app.route('/api/test/status')
def test_status():
    return jsonify(test_service.get_status())

@app.route('/api/webcam/start', methods=['POST'])
def start_webcam():
    webcam_monitor.start()
    return jsonify({'success': True, 'message': 'Webcam monitoring started'})

@app.route('/api/webcam/stop', methods=['POST'])
def stop_webcam():
    webcam_monitor.stop()
    return jsonify({'success': True, 'message': 'Webcam monitoring stopped'})

@app.route('/api/webcam/status')
def webcam_status():
    return jsonify(webcam_monitor.get_status())

# MJPEG stream endpoint for live preview
@app.route('/stream')
def stream():
    boundary = 'frame'

    def generate():
        # prepare a fallback black frame if none available yet
        fallback = None
        try:
            black = np.zeros((480, 640, 3), dtype=np.uint8)
            ok, bj = cv2.imencode('.jpg', black, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if ok:
                fallback = bj.tobytes()
        except Exception:
            fallback = None

        while True:
            frame_bytes = webcam_monitor.latest_jpeg or fallback
            if frame_bytes is None:
                time.sleep(0.1)
                continue
            yield (b"--" + boundary.encode() + b"\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            # target ~10 fps stream
            time.sleep(0.1)

    return Response(generate(), mimetype=f"multipart/x-mixed-replace; boundary={boundary}")

if __name__ == '__main__':
    print(f"🚀 Habit Tracker Backend running on port {PORT}")
    print(f"🌐 Health check: http://localhost:{PORT}/api/health")
    print(f"📋 Habits API: http://localhost:{PORT}/api/habits")
    print(f"🧪 Test API: http://localhost:{PORT}/api/test/status")
    print(f"📹 Webcam API: http://localhost:{PORT}/api/webcam/status")
    print(f"🔌 WebSocket: ws://localhost:{PORT}")
    
    # Start services
    print("🧪 Starting test service...")
    test_service.start()
    
    print("📹 Starting webcam monitoring...")
    webcam_monitor.start()
    
    try:
        import eventlet
        eventlet.wsgi.server(eventlet.listen(('', PORT)), flask_app)
    except ImportError:
        print("⚠️ eventlet not available, using development server")
        # Use Socket.IO's built-in server instead of Flask's development server
        sio.run(app, host='0.0.0.0', port=PORT, debug=False)

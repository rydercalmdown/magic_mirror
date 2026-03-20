#!/usr/bin/env python3
"""
Backend for habit tracking and webcam monitoring
Flask + Socket.IO server with OpenCV webcam monitor
"""

import os
import sys
from pathlib import Path

from flask import Flask
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

# Import our modules
from config import config
from services.test_service import TestService
from services.webcam_monitor import WebcamMonitor
from services.action_recognizer import ActionRecognizer as ARService
from services.webhook_broker import WebhookBroker
from services.action_clip_service import ActionClipService
from routes import register_routes, register_socketio_events

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

# Initialize services
test_service = TestService(min_interval=1, max_interval=5)
action_recognizer = ARService(
    models_dir=config.BASE_DIR.parent / 'training' / 'models', 
    sustained_seconds=60.0, 
    mark_habit_completed_fn=lambda name: config.mark_habit_completed(name)
)
webcam_monitor = WebcamMonitor(
    camera_index=0, 
    detection_interval=0.33, 
    action_recognizer=action_recognizer
)

# Inject Socket.IO instances into services
test_service.set_sio(sio)
webcam_monitor.set_sio(sio)

# Initialize webhook broker and attach to app
webhook_storage = config.BASE_DIR / 'data' / 'webhooks.json'
broker = WebhookBroker(storage_file=webhook_storage)
app.config['webhook_broker'] = broker

# Have the webcam monitor emit webhook events as people are detected
webcam_monitor.webhook_broker = broker

# Initialize ActionClipService for continuous 3s clip processing (store under backend/data)
data_dir = config.BASE_DIR / 'data'
clips_dir = data_dir / 'clips'
results_dir = data_dir / 'results'
action_clip_service = ActionClipService(
    clips_dir=clips_dir,
    results_dir=results_dir,
    training_dir=config.BASE_DIR.parent / 'training',
    camera_index=0,
    clip_seconds=5.0,
    target_fps=30.0
)
action_clip_service.start()

# Register routes and Socket.IO events
register_routes(app, sio, test_service, webcam_monitor)
register_socketio_events(sio, test_service, webcam_monitor)

if __name__ == '__main__':
    print(f"🚀 Habit Tracker Backend running on port {config.PORT}")
    print(f"🌐 Health check: http://localhost:{config.PORT}/api/health")
    print(f"📋 Habits API: http://localhost:{config.PORT}/api/habits")
    print(f"🧪 Test API: http://localhost:{config.PORT}/api/test/status")
    print(f"📹 Webcam API: http://localhost:{config.PORT}/api/webcam/status")
    print(f"🔌 WebSocket: ws://localhost:{config.PORT}")

    # Start services
    print("🧪 Starting test service...")
    test_service.start()

    print("📹 Starting webcam monitoring...")
    webcam_monitor.start()

    try:
        import eventlet
        eventlet.wsgi.server(eventlet.listen(('', config.PORT)), flask_app)
    except ImportError:
        print("⚠️ eventlet not available, using development server")
        # Use Socket.IO's built-in server instead of Flask's development server
        sio.run(app, host='0.0.0.0', port=config.PORT, debug=False)
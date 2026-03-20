"""
API routes for the backend
"""

import json
import time
from datetime import datetime
from flask import jsonify, request, Response, render_template
import numpy as np
import cv2

from config import config
from services.webhook_broker import WebhookBroker


def register_routes(app, sio, test_service, webcam_monitor):
    """Register all API routes with the Flask app"""
    
    @app.route('/')
    def index():
        return render_template('index.html', port=config.PORT)

    # Webhooks management
    broker: WebhookBroker = app.config.get('webhook_broker')

    @app.route('/api/webhooks/subscribe', methods=['POST'])
    def subscribe_webhook():
        if broker is None:
            return jsonify({'error': 'webhook broker unavailable'}), 503
        data = request.get_json(force=True, silent=True) or {}
        url = data.get('url')
        event = data.get('event', '*')
        ok = broker.subscribe(url, event)
        if ok:
            return jsonify({'success': True})
        return jsonify({'success': False}), 400

    @app.route('/api/webhooks/unsubscribe', methods=['POST'])
    def unsubscribe_webhook():
        if broker is None:
            return jsonify({'error': 'webhook broker unavailable'}), 503
        data = request.get_json(force=True, silent=True) or {}
        url = data.get('url')
        event = data.get('event')
        ok = broker.unsubscribe(url, event)
        return jsonify({'success': ok})

    @app.route('/api/webhooks')
    def list_webhooks():
        if broker is None:
            return jsonify({'error': 'webhook broker unavailable'}), 503
        event = request.args.get('event')
        return jsonify({'subscribers': broker.list_subscribers(event)})

    # Action results APIs
    @app.route('/api/actions')
    def list_actions():
        results_dir = config.BASE_DIR / 'data' / 'results'
        items = []
        try:
            for p in sorted(results_dir.glob('*.json'), reverse=True)[:50]:
                with open(p, 'r') as f:
                    items.append(json.load(f))
        except Exception as _:
            pass
        return jsonify({'items': items})

    @app.route('/api/actions/latest')
    def latest_action():
        results_dir = config.BASE_DIR / 'data' / 'results'
        latest = None
        try:
            files = sorted(results_dir.glob('*.json'), reverse=True)
            if files:
                with open(files[0], 'r') as f:
                    latest = json.load(f)
        except Exception as _:
            pass
        return jsonify({'latest': latest})

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
            'habits': config.settings['habits'],
            'module': config.settings['module']
        })

    @app.route('/api/habits')
    def get_habits():
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        habits = config.get_habits_for_date(date)
        return jsonify({'habits': habits})

    @app.route('/api/habits/all')
    def get_all_habits():
        data = config.get_all_habits_data()
        return jsonify({'data': data})

    @app.route('/api/habits', methods=['POST'])
    def save_habits():
        data = request.get_json()
        habits = data.get('habits', [])
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        success = config.save_habits_for_date(habits, date)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save habits'}), 500

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


def register_socketio_events(sio, test_service, webcam_monitor):
    """Register Socket.IO event handlers"""
    
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

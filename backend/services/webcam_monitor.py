"""
Webcam monitoring service for person detection using OpenCV
"""

import time
import threading
import cv2
import numpy as np
from datetime import datetime


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
        self.webhook_broker = None  # optional, set by app
        self._frame_listeners = []  # callbacks: (frame_bgr, monotonic_ts) -> None

        # Debounce/hysteresis
        self.positive_streak = 0
        self.min_positive_frames = 5  # require N consecutive positive frames to flip to True
        self.off_grace_seconds = 3.0  # seconds to wait after last seen before flipping to False

        # FPS tracking
        self._fps_window = []  # list of timestamps (monotonic)
        self._fps_window_seconds = 2.0
        self.current_fps = 0.0

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

            # Notify frame listeners (best-effort)
            try:
                ts_mono = time.monotonic()
                for cb in list(self._frame_listeners):
                    try:
                        cb(frame, ts_mono)
                    except Exception:
                        pass
            except Exception:
                pass

            # FPS window update
            try:
                now_mono = time.monotonic()
                self._fps_window.append(now_mono)
                cutoff = now_mono - self._fps_window_seconds
                # drop old timestamps
                while self._fps_window and self._fps_window[0] < cutoff:
                    self._fps_window.pop(0)
                if len(self._fps_window) >= 2:
                    duration = self._fps_window[-1] - self._fps_window[0]
                    if duration > 0:
                        self.current_fps = round((len(self._fps_window) - 1) / duration, 1)
            except Exception:
                pass

            # Encode and store latest JPEG for the stream (lower quality to reduce latency)
            try:
                ok, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 55])
                if ok:
                    self.latest_jpeg = jpg.tobytes()
            except Exception as _:
                pass

            # Convert to grayscale for detection, denoise a bit
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            try:
                gray = cv2.GaussianBlur(gray, (5, 5), 0)
                cv2.equalizeHist(gray, gray)
            except Exception:
                pass

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
                self.positive_streak += 1
                self.last_seen_time = now_dt
                if not self.person_detected and self.positive_streak >= self.min_positive_frames:
                    # switch to detected after enough consecutive positives
                    self.person_detected = True
                    self.last_detection_time = now_dt
                    print("👤 Person detection: DETECTED")
                    if hasattr(self, 'sio'):
                        self.sio.emit('personDetection', {
                            'detected': True,
                            'timestamp': self.last_detection_time.isoformat()
                        })
                    if self.webhook_broker is not None:
                        self.webhook_broker.emit('person_detected', {
                            'detected': True,
                            'timestamp': self.last_detection_time.isoformat()
                        })
                elif self.person_detected:
                    # already detected; refresh timestamps
                    self.last_detection_time = now_dt
            else:
                # no person in this frame; only flip to not detected if >3s since last_seen
                self.positive_streak = 0
                if self.person_detected and self.last_seen_time is not None:
                    delta = (now_dt - self.last_seen_time).total_seconds()
                    if delta > self.off_grace_seconds:
                        self.person_detected = False
                        print("👤 Person detection: NOT DETECTED")
                        if hasattr(self, 'sio'):
                            self.sio.emit('personDetection', {
                                'detected': False,
                                'timestamp': self.last_detection_time.isoformat() if self.last_detection_time else None
                            })
                        if self.webhook_broker is not None:
                            self.webhook_broker.emit('person_detected', {
                                'detected': False,
                                'timestamp': self.last_detection_time.isoformat() if self.last_detection_time else None
                            })

            previous_frame = gray.copy()
            time.sleep(self.detection_interval)

            # Feed frames to action recognizer only while a person is detected
            if self.person_detected and self.action_recognizer is not None:
                try:
                    self.action_recognizer.process_frame(frame, sio=getattr(self, 'sio', None))
                except Exception as _:
                    pass

        cap.release()

    def _detect_face_or_body(self, gray):
        """Detect faces or bodies using Haar cascades"""
        try:
            # Detect faces (stricter params to reduce false positives)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, flags=0, minSize=(60, 60)
            )
            if len(faces) > 0:
                return True

            # Detect bodies
            bodies = self.body_cascade.detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=5, flags=0, minSize=(80, 80)
            )
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
            'cameraIndex': self.camera_index,
            'fps': self.current_fps
        }

    def set_sio(self, sio):
        """Inject Socket.IO instance for emitting events"""
        self.sio = sio

    def register_frame_listener(self, callback):
        """Register a listener that receives (frame_bgr, ts_mono) for every captured frame."""
        self._frame_listeners.append(callback)

    def unregister_frame_listener(self, callback):
        try:
            self._frame_listeners.remove(callback)
        except ValueError:
            pass

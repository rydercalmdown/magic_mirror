"""
Test service that sends random numbers via Socket.IO
"""

import time
import threading
import random
from datetime import datetime


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
            number = random.randint(10, 99)
            print(f"🧪 Test Service: Sending random number {number} to frontend")
            # Note: sio will be injected by the main app
            if hasattr(self, 'sio'):
                self.sio.emit('randomNumber', {'number': number, 'timestamp': datetime.now().isoformat()})

            # Random interval between min and max
            interval = random.uniform(self.min_interval, self.max_interval)
            time.sleep(interval)

    def get_status(self):
        return {
            'isRunning': self.is_running,
            'minInterval': self.min_interval,
            'maxInterval': self.max_interval
        }

    def set_sio(self, sio):
        """Inject Socket.IO instance for emitting events"""
        self.sio = sio

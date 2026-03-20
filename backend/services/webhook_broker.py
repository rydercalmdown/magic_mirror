"""
Webhook broker service: manage subscribers and emit events via HTTP POST.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional
import time

import requests


class WebhookBroker:
    """A simple webhook broker that stores subscriber URLs and emits events to them.

    Subscribers are persisted to disk as a JSON file to survive restarts.
    """

    def __init__(self, storage_file: Path):
        self.storage_file = storage_file
        self._lock = threading.Lock()
        self._subscribers: List[Dict[str, str]] = []  # list of {"url": str, "event": str|"*"}
        self._load()

    def _load(self):
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    self._subscribers = data.get('subscribers', [])
            else:
                self._save()
        except Exception:
            self._subscribers = []

    def _save(self):
        try:
            with open(self.storage_file, 'w') as f:
                json.dump({'subscribers': self._subscribers}, f, indent=2)
        except Exception:
            pass

    def list_subscribers(self, event: Optional[str] = None) -> List[Dict[str, str]]:
        with self._lock:
            if event is None:
                return list(self._subscribers)
            return [s for s in self._subscribers if s.get('event') in (event, '*')]

    def subscribe(self, url: str, event: str = '*') -> bool:
        if not url or not isinstance(url, str):
            return False
        if not url.startswith('http://') and not url.startswith('https://'):
            return False
        with self._lock:
            entry = {'url': url, 'event': event or '*'}
            if entry in self._subscribers:
                return True
            self._subscribers.append(entry)
            self._save()
            return True

    def unsubscribe(self, url: str, event: Optional[str] = None) -> bool:
        with self._lock:
            before = len(self._subscribers)
            if event:
                self._subscribers = [s for s in self._subscribers if not (s.get('url') == url and s.get('event') == event)]
            else:
                self._subscribers = [s for s in self._subscribers if s.get('url') != url]
            changed = len(self._subscribers) != before
            if changed:
                self._save()
            return changed

    def emit(self, event: str, payload: Dict):
        """Emit an event to all relevant subscribers in background threads."""
        targets = self.list_subscribers(event)
        for sub in targets:
            url = sub.get('url')
            # Fire each delivery in its own thread to avoid blocking
            threading.Thread(target=self._deliver, args=(url, event, payload), daemon=True).start()

    def _deliver(self, url: str, event: str, payload: Dict):
        body = {
            'event': event,
            'timestamp': time.time(),
            'data': payload,
        }
        try:
            requests.post(url, json=body, timeout=2.5)
        except Exception:
            # Ignore webhook errors; could add retries/backoff later
            pass



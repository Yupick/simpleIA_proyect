import time
from collections import defaultdict
from threading import Lock

class RateLimiter:
    def __init__(self, requests: int, window_seconds: int):
        self.requests = requests
        self.window = window_seconds
        self._lock = Lock()
        self._buckets = defaultdict(list)  # identifier -> list[timestamps]

    def allow(self, identifier: str) -> bool:
        now = time.time()
        with self._lock:
            timestamps = self._buckets[identifier]
            # Remove expired timestamps
            cutoff = now - self.window
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            if len(timestamps) < self.requests:
                timestamps.append(now)
                return True
            return False

"""
Bounded in-memory rate limiter with LRU eviction.

Replaces the old dict + .clear() pattern that was floodable — an attacker
sending requests from 200+ IPs would flush the entire rate-limit state,
resetting limits for all legitimate IPs.

This implementation evicts the oldest entries when the dict exceeds max_keys,
and garbage-collects expired entries periodically.
"""

import time
from collections import OrderedDict


class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_sec: int = 60, max_keys: int = 1000):
        self._max_attempts = max_attempts
        self._window = window_sec
        self._max_keys = max_keys
        self._store: OrderedDict[str, list[float]] = OrderedDict()
        self._gc_counter = 0

    def is_limited(self, key: str) -> bool:
        now = time.time()

        self._gc_counter += 1
        if self._gc_counter >= 100:
            self._gc()
            self._gc_counter = 0

        attempts = self._store.get(key, [])
        attempts = [t for t in attempts if now - t < self._window]

        if len(attempts) >= self._max_attempts:
            self._store[key] = attempts
            self._store.move_to_end(key)
            return True

        attempts.append(now)
        self._store[key] = attempts
        self._store.move_to_end(key)

        while len(self._store) > self._max_keys:
            self._store.popitem(last=False)

        return False

    def _gc(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if all(now - t >= self._window for t in v)]
        for k in expired:
            del self._store[k]

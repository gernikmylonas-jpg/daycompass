"""A small in-memory limiter for repeated *failures* (wrong password, wrong journal PIN).
Successful requests are never counted. It lives in one process, which is right for a single API container;
behind several replicas you would move it to Redis."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException


class FailureLimiter:
    def __init__(self, max_failures: int, window_seconds: int):
        self.max, self.window = max_failures, window_seconds
        self._failures: dict[str, deque] = defaultdict(deque)

    def _trim(self, key: str) -> deque:
        q = self._failures[key]
        cutoff = time.monotonic() - self.window
        while q and q[0] < cutoff:
            q.popleft()
        return q

    def check(self, key: str) -> None:
        if len(self._trim(key)) >= self.max:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later")

    def fail(self, key: str) -> None:
        self._trim(key).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


logins = FailureLimiter(max_failures=8, window_seconds=600)
journal_pins = FailureLimiter(max_failures=8, window_seconds=600)

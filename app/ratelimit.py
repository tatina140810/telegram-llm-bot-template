import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding window: at most `limit` events per `window` seconds per key."""

    def __init__(self, limit: int, window: float = 60.0, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self.events: dict[int, deque] = defaultdict(deque)

    def allow(self, key: int) -> bool:
        now = self.clock()
        q = self.events[key]
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

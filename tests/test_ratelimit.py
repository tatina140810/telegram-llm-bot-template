from app.ratelimit import RateLimiter


def test_sliding_window():
    now = [0.0]
    rl = RateLimiter(limit=2, window=60, clock=lambda: now[0])
    assert rl.allow(1) and rl.allow(1) and not rl.allow(1)
    assert rl.allow(2)  # other users are independent
    now[0] = 61
    assert rl.allow(1)

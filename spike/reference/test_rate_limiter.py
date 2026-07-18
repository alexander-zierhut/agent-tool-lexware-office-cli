"""Hermetic tests for the reference RateLimiter — no real time, no network.

A fake clock + fake sleep make the pacing math exact and instant: `sleep(dt)`
advances the clock by `dt`, so the limiter behaves as if time really passed while
the test runs in microseconds. This is the standard way to test a rate limiter,
and it means the build can port these tests verbatim.

Run: `python -m pytest spike/reference/test_rate_limiter.py`
"""

from __future__ import annotations

import pytest

from rate_limiter import RateLimiter


class Clock:
    """Injectable time. `sleep` advances `now`, so no wall-clock passes."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, dt: float) -> None:
        assert dt >= 0
        self.now += dt
        self.slept += dt


@pytest.fixture
def clock():
    return Clock()


def test_first_request_is_free(clock):
    rl = RateLimiter(clock=clock.time, sleep=clock.sleep)
    assert rl.acquire() == 0.0
    assert clock.slept == 0.0


def test_no_burst_by_default_second_call_waits(clock):
    """burst=1 is the whole point — the API barely tolerates bursts, so a second
    immediate call must pace, not fire back-to-back."""
    rl = RateLimiter(rate=1.3, clock=clock.time, sleep=clock.sleep)
    rl.acquire()                       # free
    waited = rl.acquire()              # must wait ~1/rate
    assert waited == pytest.approx(1 / 1.3, abs=1e-6)


def test_spacing_matches_the_rate(clock):
    """N requests through a burst-1 limiter take ~(N-1)/rate seconds — a clean
    minimum-interval pacer."""
    rl = RateLimiter(rate=2.0, clock=clock.time, sleep=clock.sleep)
    for _ in range(11):
        rl.acquire()
    assert clock.slept == pytest.approx(10 * 0.5, abs=1e-6)   # 10 gaps of 0.5s


def test_idle_time_refills_a_token_but_not_a_burst(clock):
    """After sitting idle, exactly ONE request may go immediately (capacity 1) —
    never a pile of them."""
    rl = RateLimiter(rate=1.0, clock=clock.time, sleep=clock.sleep)
    rl.acquire()
    clock.now += 100                   # idle a long time
    assert rl.acquire() == 0.0         # one free token...
    assert rl.acquire() == pytest.approx(1.0, abs=1e-6)  # ...but the next paces


def test_penalize_halves_the_rate_and_drains(clock):
    """A 429 slipped through: the next request must pace at the NEW (slower) rate."""
    rl = RateLimiter(rate=2.0, clock=clock.time, sleep=clock.sleep)
    rl.acquire()
    rl.penalize()
    assert rl.rate == 1.0
    waited = rl.acquire()
    assert waited == pytest.approx(1 / 1.0, abs=1e-6)   # paced at the halved rate


def test_penalize_never_drops_below_the_floor(clock):
    rl = RateLimiter(rate=1.0, floor=0.5, clock=clock.time, sleep=clock.sleep)
    for _ in range(10):
        rl.penalize()
    assert rl.rate == 0.5


def test_relax_drifts_up_but_not_past_the_base(clock):
    rl = RateLimiter(rate=1.3, clock=clock.time, sleep=clock.sleep)
    rl.penalize()                      # -> 0.65
    for _ in range(50):
        rl.relax()
    assert rl.rate == pytest.approx(1.3, abs=1e-9)   # capped at the base, not above


def test_relax_is_also_capped_at_the_documented_ceiling(clock):
    rl = RateLimiter(rate=1.9, ceil=2.0, clock=clock.time, sleep=clock.sleep)
    for _ in range(50):
        rl.relax()
    assert rl.rate <= 2.0


def test_a_burst_capacity_is_honoured_when_explicitly_asked(clock):
    """burst>1 is a footgun for Lexware, but the mechanism must still be correct so
    another tool in the family can reuse this class."""
    rl = RateLimiter(rate=1.0, burst=3, clock=clock.time, sleep=clock.sleep)
    assert rl.acquire() == 0.0
    assert rl.acquire() == 0.0
    assert rl.acquire() == 0.0          # three free (the burst)
    assert rl.acquire() == pytest.approx(1.0, abs=1e-6)  # then paced

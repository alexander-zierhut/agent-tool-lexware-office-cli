"""Reference rate limiter for the Lexware Office CLI — port this into client.py.

Lexware's public API allows ~2 req/s ORG-WIDE (across all endpoints) and exposes
**no** `X-RateLimit-*` / `Retry-After` headers, so the client cannot react its way
to correctness — it must **not over-emit in the first place**. Per the user: the
CLI should just *track the rate limit and automatically delay*. That is exactly a
token bucket with a **blocking** acquire: every request calls `acquire()`, which
sleeps just long enough to stay under the ceiling. Commands never think about it.

Three design choices earned from the live sandbox (the third the hard way):

* **Target under the ceiling (default 1.3/s ≈ 0.77 s spacing).** Verified clean:
  ~30 requests at 0.75 s spacing during the data fill drew zero 429s.
* **NO burst (capacity 1).** This one was measured, not guessed: a first draft with
  `burst=3` at 1.8/s 429'd on the *third* back-to-back request. **The API's burst
  tolerance is effectively nil** — two quick calls after a quiet moment are enough
  to trip it. So the bucket holds exactly one token: strictly one request per
  interval, no bursting. `burst>1` for Lexware is a footgun; the default stays 1.
* **Adaptive: tighten on a 429.** Perfect local pacing can still 429 — a co-tenant
  integration on the same org, or server jitter. When the client's retry layer
  catches a 429 it calls `penalize()`, which drains the bucket and *halves the rate
  for the rest of this run* (floored). A one-shot command that hits the wall should
  finish slower, not fail. It drifts back up via `relax()` on sustained success.

This module is pure and side-effect-free except for `time.sleep`, so it is unit
testable with an injected clock (see `tests`). Thread-safe via a lock so a future
concurrent command shares one budget.
"""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """A blocking token-bucket pacer. Call ``acquire()`` before every request."""

    def __init__(
        self,
        rate: float = 1.3,
        burst: int = 1,
        *,
        floor: float = 0.5,
        ceil: float = 2.0,
        clock=time.monotonic,
        sleep=time.sleep,
    ) -> None:
        # rate: sustained tokens/sec (under the 2/s ceiling for jitter headroom).
        # burst: bucket capacity — how many back-to-back calls before pacing kicks
        #        in. Small on purpose; the API's own burst allowance is tiny.
        self._rate = rate
        self._base_rate = rate
        self._capacity = burst
        self._tokens = float(burst)
        self._floor = floor          # never throttle below this (progress guarantee)
        self._ceil = ceil            # never speed above the documented ceiling
        self._clock = clock
        self._sleep = sleep
        self._updated = clock()
        self._lock = threading.Lock()

    # ---- the one method the client calls before each request ----
    def acquire(self) -> float:
        """Block until a token is available, then consume it. Returns the seconds
        actually waited (0.0 if a token was ready) — handy for a progress line."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return 0.0
            wait = (1.0 - self._tokens) / self._rate
        # sleep OUTSIDE the lock so concurrent callers queue rather than serialize
        # on the sleep itself; re-acquire to consume the freshly-earned token.
        self._sleep(wait)
        with self._lock:
            self._refill()
            self._tokens = max(0.0, self._tokens - 1.0)
        return wait

    # ---- the client's retry layer calls these ----
    def penalize(self) -> None:
        """A 429 slipped through: we're over the *real* budget. Drain the bucket and
        multiplicatively lower the rate for the rest of the run (floored)."""
        with self._lock:
            self._tokens = 0.0
            self._rate = max(self._floor, self._rate * 0.5)

    def relax(self) -> None:
        """Sustained success: drift the rate back up toward the base (never above
        the ceiling). Call occasionally (e.g. every N successful requests)."""
        with self._lock:
            self._rate = min(self._base_rate, self._ceil, self._rate * 1.1)

    @property
    def rate(self) -> float:
        return self._rate

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._updated
        self._updated = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)

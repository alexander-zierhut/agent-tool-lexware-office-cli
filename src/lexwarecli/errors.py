"""Lexware-specific additions to the shared exit-code taxonomy.

0-7 are the shared family contract (0 ok · 1 generic · 3 config · 4 auth ·
5 not-found · 6 conflict · 7 validation · 130 SIGINT). 8+ are this tool's own.
"""

from __future__ import annotations

from agentcli.errors import (  # noqa: F401  (re-exported for command modules)
    ApiError,
    AuthError,
    ConfigError,
    ConflictError,
    DryRun,
    NotFoundError,
    OpError,
    ValidationError,
)


class RateLimited(OpError):
    """Exhausted the retry budget against the 2 req/s limit.

    Exit **8**. Reaching here means the client's own token bucket AND its backoff
    both gave up — almost always a *shared* budget (another integration hammering
    the same org), because our pacing alone will not 429. Its own code so an agent
    can tell "slow down / try later" apart from a hard failure.
    """

    exit_code = 8

"""HTTP client for the Lexware Office API.

Not shared with the other agent-tool CLIs — the family shares the *contract*, not
the transport, and every rule here is Lexware-shaped:

* **Auth** is a single API key: ``Authorization: Bearer <key>``.
* **The client self-paces.** The API allows ~2 req/s org-wide with NO rate-limit
  headers, so correctness means not over-emitting: every request goes through a
  blocking token bucket (the reference limiter, validated live). 429 is the
  backstop, not the plan — on one it backs the limiter off and retries.
* **A 429 can arrive as HTTP 500** ("...or rate limit exceeded") — treated as
  retryable rate-limit. A **504 may have succeeded** — never blind-retry a POST.
* **Three error envelopes** (regular / legacy IssueList / gateway) → mapped to the
  shared taxonomy. A ``406`` whose IssueList ``source == "version"`` is a CONFLICT,
  not a validation error — the mapper reads the body, not just the status.
* **Pageable pagination** with an authoritative total: page until ``last == true``
  (OpenProject's rule, NOT drone's short-page rule).
* **Optimistic locking** via ``version`` on every write.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Any, Iterator

import httpx

from .errors import (
    ApiError,
    AuthError,
    ConflictError,
    DryRun,
    NotFoundError,
    RateLimited,
    ValidationError,
)

_WRITE_METHODS = ("POST", "PATCH", "PUT", "DELETE")
_MAX_ATTEMPTS = 5


class RateLimiter:
    """Blocking token-bucket pacer — see spike/reference/rate_limiter.py for the
    full rationale and its live validation. burst=1: the API barely tolerates
    bursts, so it is strictly one request per interval."""

    def __init__(self, rate: float = 1.3, burst: int = 1, *, floor: float = 0.5, ceil: float = 2.0) -> None:
        self._rate = rate
        self._base = rate
        self._cap = burst
        self._tokens = float(burst)
        self._floor = floor
        self._ceil = ceil
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            wait = (1.0 - self._tokens) / self._rate
        time.sleep(wait)
        with self._lock:
            self._refill()
            self._tokens = max(0.0, self._tokens - 1.0)

    def penalize(self) -> None:
        with self._lock:
            self._tokens = 0.0
            self._rate = max(self._floor, self._rate * 0.5)

    def relax(self) -> None:
        with self._lock:
            self._rate = min(self._base, self._ceil, self._rate * 1.1)

    def _refill(self) -> None:
        now = time.monotonic()
        self._tokens = min(self._cap, self._tokens + (now - self._updated) * self._rate)
        self._updated = now


class Client:
    """A thin, typed wrapper over the Lexware Office REST API."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        verify_ssl: bool = True,
        timeout: float = 35.0,
        dry_run: bool = False,
        rate: float = 1.3,
        user_agent: str = "agent-tool-lexware-cli",
    ) -> None:
        self.api_root = base_url.rstrip("/") + "/v1"
        self.web_root = base_url.rstrip("/")
        self.dry_run = dry_run
        self._limiter = RateLimiter(rate=rate)
        self._ok_streak = 0
        self._client = httpx.Client(
            verify=verify_ssl,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": user_agent,
            },
        )

    # ---- plumbing ----------------------------------------------------

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.api_root}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
        content: bytes | None = None,
        raw: bool = False,
    ) -> Any:
        url = self._url(path)
        clean = {k: v for k, v in (params or {}).items() if v is not None}

        if self.dry_run and method.upper() in _WRITE_METHODS:
            raise DryRun({"method": method.upper(), "url": url, "params": clean or None, "body": json if json is not None else content})

        idempotent = method.upper() in ("GET", "HEAD", "PUT", "DELETE")
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            self._limiter.acquire()  # <-- the automatic delay; commands never see it
            try:
                resp = self._client.request(method, url, params=clean or None, json=json, content=content)
            except httpx.ConnectError as exc:
                last_exc = exc
                if attempt == _MAX_ATTEMPTS:
                    raise ApiError(f"cannot reach {self.web_root}: {exc}") from exc
                self._backoff(attempt)
                continue
            except httpx.HTTPError as exc:
                raise ApiError(f"request failed: {exc}") from exc

            # Rate limit — including the 429-disguised-as-500 case.
            if resp.status_code == 429 or self._is_500_ratelimit(resp):
                self._limiter.penalize()
                self._ok_streak = 0
                if attempt < _MAX_ATTEMPTS:
                    self._backoff(attempt, resp.headers.get("Retry-After"))
                    continue
                raise RateLimited(
                    "the Lexware API kept returning 429 after retries. The 2 req/s "
                    "limit is org-wide — another integration may be using the same "
                    "budget. Try again shortly."
                )

            # 504 may have succeeded: safe to retry only for idempotent methods.
            if resp.status_code == 504 and idempotent and attempt < _MAX_ATTEMPTS:
                self._backoff(attempt)
                continue

            if resp.status_code >= 400:
                self._raise_for_error(resp)

            # success — let the limiter drift back up occasionally
            self._ok_streak += 1
            if self._ok_streak % 10 == 0:
                self._limiter.relax()

            if raw:
                return resp.content
            if not resp.content:
                return None
            try:
                return resp.json()
            except ValueError:
                return resp.text
        raise ApiError(f"request failed after {_MAX_ATTEMPTS} attempts: {last_exc}")

    @staticmethod
    def _is_500_ratelimit(resp: httpx.Response) -> bool:
        if resp.status_code != 500:
            return False
        try:
            body = resp.json()
            return isinstance(body, dict) and "rate limit" in str(body.get("message", "")).lower()
        except ValueError:
            return "rate limit" in (resp.text or "").lower()

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None = None) -> None:
        delay = 0.6 * (2 ** (attempt - 1))
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass
        time.sleep(min(delay, 20.0) + random.uniform(0, 0.3))

    @staticmethod
    def _raise_for_error(resp: httpx.Response) -> None:
        status = resp.status_code
        try:
            body = resp.json()
        except ValueError:
            body = resp.text

        # Legacy IssueList envelope (contacts / files / bookkeeping vouchers).
        if isinstance(body, dict) and isinstance(body.get("IssueList"), list):
            issues = body["IssueList"]
            sources = [str(i.get("source", "")) for i in issues if isinstance(i, dict)]
            msg = "; ".join(
                f"{i.get('source', '?')}: {i.get('i18nKey', 'invalid')}" for i in issues if isinstance(i, dict)
            ) or "validation failed"
            # A version issue is a CONFLICT wearing a 406 (verified live).
            if "version" in sources:
                raise ConflictError(
                    "version conflict: the resource changed since you read it. "
                    "Re-fetch it and retry the update.",
                    detail=body,
                )
            if status == 404:
                raise NotFoundError(msg, detail=body)
            raise ValidationError(msg, detail=body)

        # Regular or gateway envelope.
        msg = ""
        if isinstance(body, dict):
            msg = str(body.get("message") or body.get("error") or "")
        msg = msg or (body if isinstance(body, str) else f"HTTP {status}")

        if status in (401, 403):
            raise AuthError(msg or "unauthorized", detail=body)
        if status == 404:
            raise NotFoundError(msg or "not found", detail=body)
        if status == 409:
            raise ConflictError(msg or "conflict", detail=body)
        if status in (400, 406, 415):
            raise ValidationError(msg or "invalid request", detail=body)
        raise ApiError(msg or f"HTTP {status}", status=status, detail=body)

    # ---- verbs -------------------------------------------------------

    def get(self, path: str, **kw) -> Any:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> Any:
        return self.request("POST", path, **kw)

    def put(self, path: str, **kw) -> Any:
        return self.request("PUT", path, **kw)

    def delete(self, path: str, **kw) -> Any:
        return self.request("DELETE", path, **kw)

    def profile(self) -> Any:
        return self.get("/profile")

    # ---- pagination --------------------------------------------------

    def paginate(self, path: str, *, params: dict | None = None, size: int = 100, limit: int = 0) -> Iterator[dict]:
        """Yield items across Pageable pages.

        Stops on ``last == true`` — the API has an authoritative total, so a short
        ``content`` array is NOT the end (that is drone's rule, and using it here
        would truncate). Every page request is paced by the limiter.
        """
        page = 0
        seen = 0
        while True:
            wrapper = self.get(path, params={**(params or {}), "page": page, "size": size})
            if not isinstance(wrapper, dict):
                return
            for item in wrapper.get("content") or []:
                yield item
                seen += 1
                if limit and seen >= limit:
                    return
            if wrapper.get("last") is True or page + 1 >= (wrapper.get("totalPages") or 0):
                return
            page += 1

    def close(self) -> None:
        self._client.close()

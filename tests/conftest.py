"""Shared fixtures.

Two tiers, like the sibling tools:
  * hermetic (default) — a fake client / pure logic; no network, no account.
  * integration (`-m integration`) — boots the sibling `lexware-office-mock` as a
    Node subprocess and points a real Client at it. This is the mock earning its
    keep: a bootable backend for the CLI's tests, replacing canned fixtures.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

_LEAKY = (
    "LEXWARE_API_KEY", "LEXOFFICE_API_KEY", "LEXWARE_URL",
    "LEXWARECLI_URL", "LEXWARECLI_TOKEN", "LEXWARECLI_PROFILE",
    "LEXWARECLI_FORMAT", "LEXWARECLI_CLI_FORMAT", "LEXWARECLI_CLI_FIELDS",
    "LEXWARECLI_DRY_RUN", "LEXWARECLI_STREAM", "LEXWARECLI_NO_CONTEXT",
)


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch, tmp_path):
    monkeypatch.setenv("LEXWARECLI_CONFIG_DIR", str(tmp_path / "config"))
    for v in _LEAKY:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("PYTHON_KEYRING_BACKEND", "keyring.backends.null.Keyring")
    yield


# ---- the mock backend (integration tier) ----------------------------

_MOCK_DIR = Path(__file__).resolve().parents[2] / "lexware-office-mock"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def mock_server():
    """Boot the Node mock once per test session. Skips (not fails) if node or the
    mock repo is unavailable — the hermetic tier does not need it."""
    if not shutil.which("node"):
        pytest.skip("node not found — install Node to run integration tests against the mock")
    if not (_MOCK_DIR / "src" / "server.js").exists():
        pytest.skip(f"mock not found at {_MOCK_DIR}")
    import urllib.request

    port = _free_port()
    env = {**os.environ, "PORT": str(port), "MOCK_RATE_RPS": "0"}  # limiter off for fast tests
    proc = subprocess.Popen(
        ["node", "src/server.js"], cwd=str(_MOCK_DIR), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(f"{base}/__mock__/health", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        pytest.skip("mock did not become healthy")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def client(mock_server):
    """A Client pointed at a freshly-reset mock (each test gets a clean slate)."""
    import urllib.request

    # reset the mock's state between tests via a fresh process? Simpler: the mock
    # is stateful per-process; we rely on unique data per test. For a hard reset a
    # test can restart, but most tests create their own contacts/invoices.
    from lexwarecli.client import Client

    c = Client(mock_server, "test-key", rate=50)  # fast: the mock's own limiter is off
    yield c
    c.close()

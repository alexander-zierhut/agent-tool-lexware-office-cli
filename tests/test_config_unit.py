"""Hermetic tests for profile resolution — no network, no account.

Guards the "just export LEXWARE_API_KEY" onboarding path: a token in the
environment must be enough to reach production, WITHOUT also setting LEXWARE_URL
or running `auth login`. This regressed once — the env var alone raised the very
ConfigError that then told you to set LEXWARE_API_KEY.
"""

from __future__ import annotations

import pytest
from agentcli.errors import ConfigError

from lexwareoffice.config import PROD_URL, Config


def test_env_token_alone_bootstraps_production(monkeypatch):
    monkeypatch.setenv("LEXWARE_API_KEY", "tok_live_xyz")
    prof = Config.load().resolve()
    assert prof.base_url == PROD_URL


def test_env_url_still_wins_for_sandbox(monkeypatch):
    monkeypatch.setenv("LEXWARE_API_KEY", "tok")
    monkeypatch.setenv("LEXWARE_URL", "https://api.lexware-sandbox.io")
    prof = Config.load().resolve()
    assert "sandbox" in prof.base_url


def test_no_token_no_profile_still_errors(monkeypatch):
    # With neither a stored profile, a URL, nor a token, we still guide the user.
    for v in ("LEXWARE_API_KEY", "LEXOFFICE_API_KEY", "LEXWAREOFFICE_TOKEN", "LEXWARE_URL"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ConfigError):
        Config.load().resolve()

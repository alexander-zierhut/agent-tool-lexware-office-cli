"""`auth status` is the diagnostic you run when nothing works, so it must never
fail on a missing configuration (the family contract: exit 0, configured=false).
Hermetic."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from lexwareoffice.cli import app


def test_auth_status_degrades_when_unconfigured(monkeypatch, tmp_path):
    monkeypatch.setenv("LEXWAREOFFICE_CONFIG_DIR", str(tmp_path / "nothing-here"))
    for v in ("LEXWAREOFFICE_TOKEN", "LEXWARE_API_KEY", "LEXWARE_URL", "LEXWAREOFFICE_BASE_URL"):
        monkeypatch.delenv(v, raising=False)
    r = CliRunner().invoke(app, ["auth", "status"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert data["configured"] is False
    assert "auth login" in data["reason"]

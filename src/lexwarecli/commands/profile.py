"""`lexware-cli profile` — the connected organisation, and a reachability check."""

from __future__ import annotations

import typer

from ..errors import OpError
from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


@app.command("show")
def show(ctx: typer.Context) -> None:
    """The connected organisation (`GET /v1/profile`): company, features, tax type."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().profile())


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    """Diagnose the connection: is the key valid, which org, what features?

    Never raises — returning the report is its job.
    """
    obj = ctx_obj(ctx)
    checks = []

    def probe(name, fn):
        try:
            return {"check": name, "ok": True, "detail": fn()}
        except OpError as exc:  # NotFoundError and ApiError are siblings — catch the base
            return {"check": name, "ok": False, "detail": str(exc)}

    try:
        client = obj.client()
    except OpError as exc:
        obj.emitter.emit({"ok": False, "checks": [{"check": "config", "ok": False, "detail": str(exc)}]})
        return

    prof = probe("profile", client.profile)
    checks.append(prof)
    if prof["ok"]:
        d = prof["detail"]
        checks.append({"check": "identity", "ok": True, "detail": {"companyName": d.get("companyName"), "organizationId": d.get("organizationId"), "taxType": d.get("taxType"), "businessFeatures": d.get("businessFeatures")}})
    # a cheap read that needs a valid key + reachable API
    checks.append(probe("countries (read access)", lambda: f"{len(client.get('/countries') or [])} countries"))

    ok = all(c["ok"] for c in checks)
    obj.emitter.emit({"ok": ok, "profile": obj.config.resolve().base_url, "checks": checks})

"""Sticky session defaults, per profile."""

from __future__ import annotations

import typer

from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)

KNOWN_KEYS = ["contact"]


@app.command("show")
def show(ctx: typer.Context) -> None:
    obj = ctx_obj(ctx)
    obj.emitter.emit({"profile": obj.config.active_profile_name(), "context": obj.config.context})


@app.command("set")
def set_(ctx: typer.Context, contact: str = typer.Option(None, "--contact", help="Default contact id.")) -> None:
    obj = ctx_obj(ctx)
    name = obj.config.active_profile_name()
    cur = dict(obj.config.contexts.get(name) or {})
    if contact is not None:
        cur["contact"] = contact
    obj.config.contexts[name] = cur
    obj.config.save()
    obj.emitter.emit({"profile": name, "context": cur})


@app.command("clear")
def clear(ctx: typer.Context) -> None:
    obj = ctx_obj(ctx)
    obj.config.contexts.pop(obj.config.active_profile_name(), None)
    obj.config.save()
    obj.emitter.emit({"cleared": True})

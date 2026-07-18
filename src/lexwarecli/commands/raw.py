"""The escape hatch: call any API path directly (still paced + error-mapped)."""

from __future__ import annotations

import json as jsonlib

import typer

from ..errors import ValidationError
from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


def _params(pairs):
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise ValidationError(f"--param wants key=value, got {p!r}.")
        k, v = p.split("=", 1)
        out[k] = v
    return out


def _body(data):
    if not data:
        return None
    try:
        return jsonlib.loads(data)
    except ValueError as exc:
        raise ValidationError(f"--data must be JSON: {exc}") from exc


@app.command("get")
def get(ctx: typer.Context, path: str = typer.Argument(..., help="e.g. /profile or /voucherlist"), param: list[str] = typer.Option(None, "--param")) -> None:
    """GET any path (relative to /v1). Example: `raw get /countries`."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get(path, params=_params(param)))


@app.command("post")
def post(ctx: typer.Context, path: str = typer.Argument(...), data: str = typer.Option(None, "--data"), param: list[str] = typer.Option(None, "--param")) -> None:
    """POST any path with a JSON --data body."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().post(path, json=_body(data), params=_params(param)))


@app.command("put")
def put(ctx: typer.Context, path: str = typer.Argument(...), data: str = typer.Option(None, "--data")) -> None:
    """PUT any path with a JSON --data body."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().put(path, json=_body(data)))


@app.command("delete")
def delete(ctx: typer.Context, path: str = typer.Argument(...)) -> None:
    """DELETE any path."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().delete(path))

"""View & change CLI settings."""

from __future__ import annotations

import typer

from agentcli import OutputFormat

from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


@app.command("show")
def show(ctx: typer.Context) -> None:
    from ..config import config_path

    obj = ctx_obj(ctx)
    obj.emitter.emit({
        "default_format": obj.config.default_format,
        "current_profile": obj.config.current_profile,
        "config_path": str(config_path()),
    })


@app.command("set-format")
def set_format(ctx: typer.Context, fmt: str = typer.Argument(..., help="json | table | markdown | csv")) -> None:
    obj = ctx_obj(ctx)
    OutputFormat.coerce(fmt)  # validate
    obj.config.default_format = fmt
    obj.config.save()
    obj.emitter.emit({"default_format": fmt})


@app.command("path")
def path(ctx: typer.Context) -> None:
    from ..config import config_path

    ctx_obj(ctx).emitter.emit({"config_path": str(config_path())})

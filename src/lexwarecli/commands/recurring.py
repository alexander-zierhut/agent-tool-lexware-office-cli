"""Recurring templates — the patterns that auto-generate invoices. Read-only."""

from __future__ import annotations

import typer

from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def list_(ctx: typer.Context, limit: int = typer.Option(100, "--limit")) -> None:
    """List recurring templates (paginated)."""
    obj = ctx_obj(ctx)
    rows = list(obj.client().paginate("/recurring-templates", size=100, limit=limit))
    obj.emitter.emit(rows, columns=["id", "title", "voucherStatus"])


@app.command("get")
def get(ctx: typer.Context, template_id: str = typer.Argument(...)) -> None:
    """Retrieve one recurring template."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get(f"/recurring-templates/{template_id}"))

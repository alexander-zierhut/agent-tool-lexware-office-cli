"""Helpers shared by command modules."""

from __future__ import annotations

import typer

from ..appctx import AppContext


def ctx_obj(ctx: typer.Context) -> AppContext:
    obj = getattr(ctx, "obj", None)
    if obj is None:
        obj = AppContext()
        ctx.obj = obj
    return obj

"""Bookkeeping vouchers — the accounting-entry resource (`/v1/vouchers`).

Distinct from sales documents: these are how income/expense entries and uploaded
receipts are booked. The status vocabulary is the RESOURCE one
(open/paid/paidoff/voided/...) — there is no derived `overdue` here.
"""

from __future__ import annotations

import typer

from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def list_(
    ctx: typer.Context,
    number: str = typer.Option(None, "--number", help="Filter by voucherNumber."),
    limit: int = typer.Option(100, "--limit"),
) -> None:
    """List bookkeeping vouchers (paginated)."""
    obj = ctx_obj(ctx)
    params = {}
    if number:
        params["voucherNumber"] = number
    rows = list(obj.client().paginate("/vouchers", params=params, size=100, limit=limit))
    obj.emitter.emit(rows, columns=["id", "voucherNumber", "voucherType", "voucherStatus", "voucherDate", "totalGrossAmount"])


@app.command("get")
def get(ctx: typer.Context, voucher_id: str = typer.Argument(...)) -> None:
    """Retrieve one bookkeeping voucher."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get(f"/vouchers/{voucher_id}"))


@app.command("delete")
def delete(ctx: typer.Context, voucher_id: str = typer.Argument(...), yes: bool = typer.Option(False, "--yes", "-y")) -> None:
    """Delete a bookkeeping voucher."""
    obj = ctx_obj(ctx)
    if not yes and obj.interactive:
        typer.confirm(f"Delete voucher {voucher_id}?", abort=True)
    obj.client().delete(f"/vouchers/{voucher_id}")
    obj.emitter.emit({"id": voucher_id, "deleted": True})

"""Reference data — countries, posting categories, payment conditions, print layouts.

Read-only lookup tables. Returned as bare arrays by the API (not paginated).
"""

from __future__ import annotations

import typer

from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


@app.command("countries")
def countries(ctx: typer.Context) -> None:
    """ISO countries with their tax classification (de / intraCommunity / thirdPartyCountry)."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get("/countries"), columns=["countryCode", "countryNameEN", "taxClassification"])


@app.command("posting-categories")
def posting_categories(ctx: typer.Context) -> None:
    """Booking categories for vouchers (income vs outgo)."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get("/posting-categories"), columns=["id", "name", "type", "groupName"])


@app.command("payment-conditions")
def payment_conditions(ctx: typer.Context) -> None:
    """The organisation's payment-term templates."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get("/payment-conditions"), columns=["id", "paymentTermLabel", "paymentTermDuration", "organizationDefault"])


@app.command("print-layouts")
def print_layouts(ctx: typer.Context) -> None:
    """Document print layouts available to the organisation."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get("/print-layouts"), columns=["id", "name", "default"])

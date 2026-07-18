"""Webhooks — Lexware's event-subscriptions. Get told when things change.

`event-subscriptions` is how you register a callback URL for an event type
(e.g. `contact.changed`, `invoice.created`). Lexware POSTs to your URL when it
fires. This is the "if that happens, let me know" surface.
"""

from __future__ import annotations

import typer

from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)

# Documented Lexware event types (resource.action). Not exhaustively enforced —
# the API validates — but offered as help so an agent knows what to subscribe to.
KNOWN_EVENTS = (
    "contact.created", "contact.changed", "contact.deleted",
    "invoice.created", "invoice.changed", "invoice.deleted",
    "quotation.created", "quotation.changed",
    "credit-note.created", "credit-note.changed",
    "order-confirmation.created", "delivery-note.created",
    "voucher.created", "voucher.changed", "voucher.deleted",
    "payment.changed", "recurring-template.changed",
    "token.revoked",
)


@app.command("list")
def list_(ctx: typer.Context) -> None:
    """List all webhook subscriptions."""
    obj = ctx_obj(ctx)
    data = obj.client().get("/event-subscriptions")
    rows = data.get("content", data) if isinstance(data, dict) else data
    obj.emitter.emit(rows, columns=["subscriptionId", "eventType", "callbackUrl", "createdDate"])


@app.command("get")
def get(ctx: typer.Context, subscription_id: str = typer.Argument(..., help="Subscription id.")) -> None:
    """Retrieve one subscription."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get(f"/event-subscriptions/{subscription_id}"))


@app.command("subscribe")
def subscribe(
    ctx: typer.Context,
    event: str = typer.Option(..., "--event", help=f"Event type, e.g. invoice.created. Known: {', '.join(KNOWN_EVENTS[:6])}, …"),
    url: str = typer.Option(..., "--url", help="Your HTTPS callback URL; Lexware POSTs the event here."),
) -> None:
    """Subscribe to an event — register a callback URL Lexware will POST to.

    Preview with `--dry-run`. The callback must be a reachable HTTPS endpoint;
    Lexware sends the event id + affected resource id, and you fetch the detail.
    """
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().post("/event-subscriptions", json={"eventType": event, "callbackUrl": url}))


@app.command("delete")
def delete(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription id."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation."),
) -> None:
    """Delete a webhook subscription (stop receiving that event)."""
    obj = ctx_obj(ctx)
    if not yes and obj.interactive:
        typer.confirm(f"Delete subscription {subscription_id}?", abort=True)
    obj.client().delete(f"/event-subscriptions/{subscription_id}")
    obj.emitter.emit({"subscriptionId": subscription_id, "deleted": True})


@app.command("events")
def events(ctx: typer.Context) -> None:
    """List the event types you can subscribe to."""
    ctx_obj(ctx).emitter.emit([{"eventType": e} for e in KNOWN_EVENTS], columns=["eventType"])

"""Invoices — list (via voucherlist), get, create, finalize, PDF."""

from __future__ import annotations

import base64
import binascii
import subprocess
import sys
from pathlib import Path

import typer

from ..errors import ConflictError, ValidationError
from ._shared import ctx_obj, recreate_body_from

app = typer.Typer(no_args_is_help=True)


def _as_pdf_bytes(data: object) -> bytes | None:
    """Return raw PDF bytes, or None if `data` isn't a PDF.

    Normally the server (asked with `Accept: application/pdf`) returns raw bytes
    starting with `%PDF-`. As a belt-and-braces fallback we also accept a
    base64-encoded PDF (`JVBERi0…`), which is what Lexware hands back when the
    request's Accept is `application/json` — so the download still works even if
    the Accept override is ever lost.
    """
    if not isinstance(data, (bytes, bytearray)):
        return None
    if data[:5] == b"%PDF-":
        return bytes(data)
    try:
        decoded = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return None
    return decoded if decoded[:5] == b"%PDF-" else None


@app.command("list")
def list_(
    ctx: typer.Context,
    status: str = typer.Option("open", "--status", help="draft | open | overdue | paid | voided."),
    limit: int = typer.Option(100, "--limit", help="Max invoices (0 = all)."),
) -> None:
    """List invoices via the voucherlist hub (the only list view). A status is
    required by the API; defaults to `open`. Rows carry contact/due/open amounts."""
    obj = ctx_obj(ctx)
    rows = list(
        obj.client().paginate(
            "/voucherlist",
            params={"voucherType": "invoice,salesinvoice", "voucherStatus": status},
            size=100,
            limit=limit,
        )
    )
    obj.emitter.emit(rows, columns=["voucherNumber", "voucherStatus", "contactName", "dueDate", "openAmount", "totalAmount", "currency"])


@app.command("get")
def get(ctx: typer.Context, invoice_id: str = typer.Argument(..., help="Invoice id (UUID).")) -> None:
    """Retrieve one invoice (the full object)."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get(f"/invoices/{invoice_id}"))


@app.command("payments")
def payments(ctx: typer.Context, invoice_id: str = typer.Argument(..., help="Invoice id (UUID).")) -> None:
    """Payment status of an invoice: what's open, what's been paid, and how.

    Reports `openAmount`, `paymentStatus` (balanced | openRevenue) and the payment
    items. Note this shows the STORED status (`open`), never the derived `overdue`
    — aging lives only in `receivables` / `invoice list`.
    """
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get(f"/payments/{invoice_id}"))


@app.command("pdf")
def pdf(
    ctx: typer.Context,
    invoice_id: str = typer.Argument(..., help="Invoice id (UUID). Must be finalized."),
    out: str = typer.Option(None, "--out", help="Where to save the PDF (default: ./<voucherNumber>.pdf)."),
    open_: bool = typer.Option(False, "--open", help="Open the PDF in the system viewer (human affordance; no-ops headless)."),
) -> None:
    """Download an invoice's PDF, and optionally open it for preview.

    A draft cannot be rendered (the API returns 409) — finalize it first. The PDF
    is the one binary carve-out: it is written to a file and the JSON reports the
    path, never dumped to stdout.
    """
    obj = ctx_obj(ctx)
    client = obj.client()
    try:
        # `Accept: application/pdf` is required — with the client's default
        # `Accept: application/json`, Lexware base64-encodes the PDF.
        data = client.get(f"/invoices/{invoice_id}/file", raw=True, params={}, accept="application/pdf")
    except ConflictError:
        raise ConflictError(
            "cannot render a draft invoice: a draft has no PDF. The API cannot finalize an "
            "existing draft in place — issue it with `lexware-office invoice create --from <id> "
            "--finalize` (this creates a new, numbered invoice), then download that document's PDF."
        )
    data = _as_pdf_bytes(data)
    if data is None:
        raise ValidationError("the server did not return a PDF for this invoice.")

    dest = Path(out) if out else Path(f"{_number(client, invoice_id)}.pdf")
    dest.write_bytes(data)
    result = {"pdf": str(dest.resolve()), "bytes": len(data), "opened": False}
    if open_:
        result["opened"] = _open_file(dest)
    obj.emitter.emit(result)


@app.command("finalize")
def finalize(ctx: typer.Context, invoice_id: str = typer.Argument(..., help="Draft invoice id.")) -> None:
    """Finalize an existing draft — NOT supported in place by the API.

    The public API has no PUT/finalize-existing and no DELETE on invoices: the only
    way to issue a document is at CREATE time with `?finalize=true`. To finalize a
    pre-existing (e.g. UI-created) draft, recreate it issued with
    `invoice create --from <id> --finalize`, which reads the full draft and posts a
    new, numbered invoice. The original draft cannot be removed via the API.
    """
    obj = ctx_obj(ctx)  # noqa: F841 — keep the DI/first-run wiring consistent
    raise ValidationError(
        "the public API cannot finalize an existing draft in place (no PUT, no DELETE). "
        "Recreate it issued with `lexware-office invoice create --from "
        f"{invoice_id} --finalize` (this creates a new, numbered invoice); the original "
        "draft remains and must be removed in the Lexware Office UI."
    )


@app.command("create")
def create(
    ctx: typer.Context,
    contact_id: str = typer.Option(None, "--contact", help="Customer contact id."),
    name: str = typer.Option(None, "--item", help="Line item name."),
    net: float = typer.Option(None, "--net", help="Net unit price (EUR)."),
    tax: float = typer.Option(19, "--tax", help="Tax rate percent."),
    quantity: float = typer.Option(1, "--qty"),
    term_days: int = typer.Option(14, "--term-days", help="Payment term (days) -> due date."),
    from_id: str = typer.Option(None, "--from", help="Copy an existing draft (or any invoice) in FULL and recreate it; with --finalize it is issued with a NEW number. Mutually exclusive with --contact/--item."),
    finalize: bool = typer.Option(False, "--finalize", help="Finalize immediately (assigns a number, one-way)."),
) -> None:
    """Create an invoice (draft by default; `--finalize` issues it).

    With --from <id>, GET that invoice, strip its read-only/computed fields and
    recreate it in full. This is how you finalize a pre-existing (e.g. UI-created)
    draft: the API has no in-place finalize, so --finalize here issues a NEW,
    numbered invoice. The source draft is left untouched (the API cannot delete it).
    """
    from datetime import date

    obj = ctx_obj(ctx)
    if from_id and (contact_id or name or net is not None):
        raise ValidationError("use --from OR --contact/--item, not both.")
    if not from_id and not (contact_id and name and net is not None):
        raise ValidationError("need --from <draft-id>, or --contact, --item and --net, to create an invoice.")

    if from_id:
        client = obj.client()
        src = client.get(f"/invoices/{from_id}")
        body, preceding = recreate_body_from(src, money=True)
        params = {}
        if preceding:
            params["precedingSalesVoucherId"] = preceding
        if finalize:
            params["finalize"] = "true"
        res = client.post("/invoices", json=body, params=params or None)
        out = dict(res) if isinstance(res, dict) else {"result": res}
        out["from"] = from_id
        out["finalized"] = bool(finalize)
        out["note"] = (
            f"original draft {from_id} still exists; the API cannot delete it — "
            "remove it in the Lexware Office UI if unwanted."
        )
        obj.emitter.emit(out)
        return

    today = date.today().isoformat() + "T00:00:00.000+02:00"
    body = {
        "voucherDate": today,
        "address": {"contactId": contact_id},
        "lineItems": [{"type": "custom", "name": name, "quantity": quantity, "unitName": "Stück", "unitPrice": {"currency": "EUR", "netAmount": net, "taxRatePercentage": tax}}],
        "totalPrice": {"currency": "EUR"},
        "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": today},
        "paymentConditions": {"paymentTermLabel": f"Zahlbar in {term_days} Tagen", "paymentTermDuration": term_days},
    }
    params = {"finalize": "true"} if finalize else None
    obj.emitter.emit(obj.client().post("/invoices", json=body, params=params))


def _number(client, invoice_id: str) -> str:
    try:
        inv = client.get(f"/invoices/{invoice_id}")
        return inv.get("voucherNumber") or invoice_id
    except Exception:
        return invoice_id


def _open_file(path: Path) -> bool:
    """Open in the system viewer; return whether we tried. No-op headless."""
    import os

    if os.environ.get("CI") == "true" or (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")):
        return False
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False

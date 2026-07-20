"""Factory for the sales-document command groups.

Quotations, order-confirmations, credit-notes, delivery-notes,
down-payment-invoices and dunnings share invoices' shape (create draft/finalize,
get, list via voucherlist, PDF). This builds one Typer group per type from a small
config, so the six stay consistent and the differences (read-only, no money,
requires a preceding doc) are declared, not copy-pasted.
"""

from __future__ import annotations

from datetime import date

import typer

from ..errors import ConflictError, ValidationError

# A sales-doc type's shape. `voucherlist_type` is the value voucherlist filters on
# (matches the mock; some real-API values may differ — see spike/LIVE_FINDINGS).
SALES_DOCS = {
    "quotation": dict(collection="quotations", vtype="quotation", money=True, expires=True),
    "order-confirmation": dict(collection="order-confirmations", vtype="orderConfirmation", money=True),
    "credit-note": dict(collection="credit-notes", vtype="creditNote", money=True, pursue=True),
    "delivery-note": dict(collection="delivery-notes", vtype="deliveryNote", money=False),
    "down-payment-invoice": dict(collection="down-payment-invoices", vtype="downPaymentInvoice", money=True, read_only=True),
    "dunning": dict(collection="dunnings", vtype="dunning", money=True, requires_preceding=True, no_finalize=True),
}


def _today_iso() -> str:
    return date.today().isoformat() + "T00:00:00.000+02:00"


def make_group(name: str) -> typer.Typer:
    cfg = SALES_DOCS[name]
    collection = cfg["collection"]
    app = typer.Typer(no_args_is_help=True)

    @app.command("list")
    def list_(
        ctx: typer.Context,
        status: str = typer.Option("draft", "--status", help="draft | open | ... (voucherlist status)."),
        limit: int = typer.Option(100, "--limit", help="Max results (0 = all)."),
    ) -> None:
        """List via the voucherlist hub (the only list view; a status is required)."""
        from ._shared import ctx_obj

        obj = ctx_obj(ctx)
        rows = list(obj.client().paginate("/voucherlist", params={"voucherType": cfg["vtype"], "voucherStatus": status}, size=100, limit=limit))
        obj.emitter.emit(rows, columns=["voucherNumber", "voucherStatus", "contactName", "totalAmount", "currency", "voucherDate"])

    @app.command("get")
    def get(ctx: typer.Context, doc_id: str = typer.Argument(..., help=f"{name} id (UUID).")) -> None:
        """Retrieve one document (the full object)."""
        from ._shared import ctx_obj

        obj = ctx_obj(ctx)
        obj.emitter.emit(obj.client().get(f"/{collection}/{doc_id}"))

    if not cfg.get("read_only"):

        @app.command("create")
        def create(
            ctx: typer.Context,
            contact_id: str = typer.Option(None, "--contact", help="Contact id."),
            item: str = typer.Option(None, "--item", help="Line item name."),
            net: float = typer.Option(None, "--net", help="Net unit price (EUR). Omit for delivery notes."),
            tax: float = typer.Option(19, "--tax", help="Tax rate percent."),
            qty: float = typer.Option(1, "--qty"),
            from_id: str = typer.Option(None, "--from", help="Copy an existing draft (or any doc) in FULL and recreate it; with --finalize it is issued with a NEW number. Mutually exclusive with --contact/--item."),
            preceding: str = typer.Option(None, "--preceding", help="Preceding sales-voucher id (pursue / required for dunnings)."),
            finalize: bool = typer.Option(False, "--finalize", help="Finalize immediately (assigns a number; one-way)."),
        ) -> None:
            """Create the document (draft by default; --finalize issues it).

            With --from <id>, GET that document, strip its read-only/computed fields
            and recreate it in full (all line items, intro/remark/title, dates). This
            is how you finalize a pre-existing (e.g. UI-created) draft: the API has no
            in-place finalize, so --finalize here issues a NEW, numbered document. The
            source draft is left untouched — the API cannot delete it.
            """
            from ._shared import ctx_obj, recreate_body_from

            obj = ctx_obj(ctx)
            if from_id and (contact_id or item or net is not None):
                raise ValidationError("use --from OR --contact/--item, not both.")
            if not from_id and not (contact_id and item):
                raise ValidationError(f"need --from <draft-id>, or --contact and --item, to create a {name}.")

            if from_id:
                client = obj.client()
                src = client.get(f"/{collection}/{from_id}")
                body, src_preceding = recreate_body_from(src, money=cfg["money"])
                preceding = preceding or src_preceding
                do_finalize = bool(finalize and not cfg.get("no_finalize"))
                params: dict = {}
                if preceding:
                    params["precedingSalesVoucherId"] = preceding
                if do_finalize:
                    params["finalize"] = "true"
                res = client.post(f"/{collection}", json=body, params=params or None)
                out = dict(res) if isinstance(res, dict) else {"result": res}
                out["from"] = from_id
                out["finalized"] = do_finalize
                out["note"] = (
                    f"original draft {from_id} still exists; the API cannot delete it — "
                    "remove it in the Lexware Office UI if unwanted."
                )
                obj.emitter.emit(out)
                return

            if cfg.get("requires_preceding") and not preceding:
                raise ValidationError(f"a --preceding <invoice-id> is required for a {name}.")
            today = _today_iso()
            line: dict = {"type": "custom", "name": item, "quantity": qty, "unitName": "Stück"}
            if cfg["money"]:
                line["unitPrice"] = {"currency": "EUR", "netAmount": net or 0.0, "taxRatePercentage": tax}
            body: dict = {
                "voucherDate": today,
                "address": {"contactId": contact_id},
                "lineItems": [line],
                "taxConditions": {"taxType": "net"},
                "shippingConditions": {"shippingType": "none", "shippingDate": today},
            }
            if cfg["money"]:
                body["totalPrice"] = {"currency": "EUR"}
            if cfg.get("expires"):
                body["expirationDate"] = (date.today().replace(day=1)).isoformat() + "T00:00:00.000+02:00"
            params = {}
            if preceding:
                params["precedingSalesVoucherId"] = preceding
            if finalize and not cfg.get("no_finalize"):
                params["finalize"] = "true"
            try:
                obj.emitter.emit(obj.client().post(f"/{collection}", json=body, params=params or None))
            except ConflictError:
                raise
    else:
        @app.command("create", hidden=True)
        def create_readonly(ctx: typer.Context) -> None:
            """(read-only resource)."""
            raise ValidationError(f"{name}s are read-only via the API; they cannot be created here.")

    if cfg.get("money") and not cfg.get("read_only"):
        @app.command("pdf")
        def pdf(
            ctx: typer.Context,
            doc_id: str = typer.Argument(..., help="Document id (must be finalized)."),
            out: str = typer.Option(None, "--out", help="Where to save the PDF."),
            open_: bool = typer.Option(False, "--open", help="Open in the system viewer (no-ops headless)."),
        ) -> None:
            """Download the document's PDF (must be finalized)."""
            from pathlib import Path

            from ._shared import ctx_obj
            from .invoice import _as_pdf_bytes, _open_file

            obj = ctx_obj(ctx)
            try:
                # Accept: application/pdf — else Lexware base64-encodes the body.
                data = obj.client().get(f"/{collection}/{doc_id}/file", raw=True, accept="application/pdf")
            except ConflictError:
                raise ConflictError(
                    f"cannot render a draft {name}: a draft has no PDF. The API cannot finalize an "
                    f"existing draft in place — issue it with `lexware-office {name} create --from <id> "
                    f"--finalize` (this creates a new, numbered {name}), then download that document's PDF."
                )
            data = _as_pdf_bytes(data)
            if data is None:
                raise ValidationError("the server did not return a PDF.")
            dest = Path(out) if out else Path(f"{name}-{doc_id[:8]}.pdf")
            dest.write_bytes(data)
            result = {"pdf": str(dest.resolve()), "bytes": len(data), "opened": _open_file(dest) if open_ else False}
            obj.emitter.emit(result)

    return app

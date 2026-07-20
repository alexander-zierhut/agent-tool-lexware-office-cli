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


# Fields a GET on a sales document / invoice carries that are read-only or
# server-computed, so they MUST NOT be sent back on a create (the real API 400s on
# a body with read-only fields — spike/research/invoices.md:22/796). Stripping them
# is what lets `create --from <id>` recreate a draft faithfully.
_STRIP_TOP = frozenset({
    "id",
    "version",
    "voucherNumber",
    "voucherStatus",
    "voucherType",  # read-only: the endpoint's path already fixes the type
    "createdDate",
    "updatedDate",
    "dueDate",  # read-only: derived server-side from paymentConditions
    "files",
    "organizationId",
    "taxAmounts",
    "archived",
    "electronicDocumentProfile",
    "relatedVouchers",
})


def recreate_body_from(doc: dict, *, money: bool) -> tuple[dict, str | None]:
    """Build a clean create body from a fetched sales document.

    Copies the full content (all line items, intro/remark/title, dates, conditions)
    while stripping the read-only/computed fields the API refuses on write, so the
    result can be POSTed to recreate the document (optionally finalized, which
    assigns a NEW number). The real API has no PUT/finalize-in-place, so recreation
    is the only way to issue a pre-existing (e.g. UI-created) draft.

    Returns ``(body, preceding_id)`` where ``preceding_id`` is the source's own
    preceding link (from ``relatedVouchers[0]``) so a pursued chain is preserved.
    ``money=False`` (delivery notes) drops per-line ``unitPrice`` — those types
    carry no prices.
    """
    body = {k: v for k, v in doc.items() if k not in _STRIP_TOP and v is not None}
    if isinstance(body.get("lineItems"), list):
        clean_lines = []
        for li in body["lineItems"]:
            if not isinstance(li, dict):
                clean_lines.append(li)
                continue
            li = dict(li)
            li.pop("id", None)
            li.pop("lineItemAmount", None)
            if not money:
                li.pop("unitPrice", None)
            clean_lines.append(li)
        body["lineItems"] = clean_lines
    if isinstance(body.get("totalPrice"), dict):
        # Keep the writable INPUTS (currency + any total discount the user set);
        # drop only the computed totals (totalNet/Gross/Tax). Collapsing to just
        # currency would silently drop a draft's discount and over-bill the reissue.
        src_tp = body["totalPrice"]
        tp = {"currency": src_tp.get("currency", "EUR")}
        for k in ("totalDiscountAbsolute", "totalDiscountPercentage"):
            if src_tp.get(k) is not None:
                tp[k] = src_tp[k]
        body["totalPrice"] = tp
    related = doc.get("relatedVouchers") or []
    preceding = related[0].get("id") if related and isinstance(related[0], dict) else None
    return body, preceding

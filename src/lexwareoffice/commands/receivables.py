"""`lexware-office receivables` — the killer feature.

The Lexware API answers per-invoice and refuses the aggregate. This command sweeps
`voucherlist` once (paced under the rate limit), then totals what is owed, ages it,
rolls it up per customer, and lists who to chase — none of which the API will do.
"""

from __future__ import annotations

from datetime import date

import typer

from ..errors import OpError
from ..receivables import by_customer, dunning_candidates, enrich, summarise
from ._shared import ctx_obj

app = typer.Typer()

# Invoice types that represent receivables, and the open/overdue statuses to sweep.
_TYPES = "invoice,salesinvoice"
_OPEN_STATUSES = ("open", "overdue")

EXIT_HAS_OVERDUE = 20


def receivables(
    ctx: typer.Context,
    view: str = typer.Option("aging", "--view", help="aging | customers | dunning"),
    min_days: int = typer.Option(1, "--min-days", help="For --view dunning: only invoices at least this many days overdue."),
    exit_code: bool = typer.Option(False, "--exit-code", help="Exit 20 if anything is overdue (for scripts/CI)."),
) -> None:
    """Who owes me money, how overdue, and who do I chase?

    Sweeps every open/overdue invoice via `voucherlist` and derives:
      * `aging` (default) — the total outstanding + the 0-30/31-60/61-90/90+ ladder,
      * `customers` — per-customer rollup, worst first,
      * `dunning` — overdue invoices worth chasing, worst first.

    Sums **openAmount** (not the invoice total): a partial payment lowers the
    balance while the invoice may still be overdue. Findings are not failures —
    this exits 0 even with money overdue; use `--exit-code` to branch on it.
    """
    obj = ctx_obj(ctx)
    client = obj.client()

    # One paced sweep of open+overdue. `open` already includes overdue rows, so a
    # single status query is enough — but we ask both and de-dupe by id to be
    # robust to server-side quirks.
    rows_raw: dict[str, dict] = {}
    for status in _OPEN_STATUSES:
        try:
            for v in client.paginate("/voucherlist", params={"voucherType": _TYPES, "voucherStatus": status}):
                if v.get("id"):
                    rows_raw[v["id"]] = v
        except OpError:
            # e.g. a status not accepted for this org — skip it, keep the rest.
            continue

    rows = enrich(rows_raw.values(), today=date.today())

    if view == "customers":
        payload = {"asOf": date.today().isoformat(), "customers": by_customer(rows)}
        obj.emitter.emit(
            payload["customers"],
            columns=[("Customer", "contactName"), ("Open", "open"), ("Overdue", "overdue"), ("Invoices", "count"), ("MaxDaysOverdue", "maxDaysOverdue")],
            title="Receivables by customer",
        )
    elif view == "dunning":
        cands = dunning_candidates(rows, min_days=min_days)
        payload = [
            {"voucherNumber": r.voucherNumber, "contactName": r.contactName, "openAmount": r.openAmount, "currency": r.currency, "daysOverdue": r.daysOverdue, "dueDate": r.dueDate}
            for r in cands
        ]
        obj.emitter.emit(payload, columns=["voucherNumber", "contactName", "openAmount", "daysOverdue", "dueDate"], title="Dunning candidates")
    else:  # aging
        a = summarise(rows)
        payload = {
            "asOf": date.today().isoformat(),
            "currency": a.currency,
            "totalOutstanding": a.total,
            "totalOverdue": a.overdue,
            "openInvoices": a.count,
            "overdueInvoices": a.overdueCount,
            "aging": [{"bucket": b, "amount": a.buckets[b], "invoices": a.bucketCounts[b]} for b in a.buckets],
        }
        obj.emitter.emit(payload["aging"], columns=[("Bucket", "bucket"), ("Amount", "amount"), ("Invoices", "invoices")], title=f"AR aging — {a.total} {a.currency} outstanding, {a.overdue} overdue")
        obj.emitter.message(f"{a.count} open invoice(s), {a.overdueCount} overdue. Total {a.total} {a.currency}; overdue {a.overdue} {a.currency}.")

    if exit_code and any(r.daysOverdue > 0 for r in rows):
        raise typer.Exit(code=EXIT_HAS_OVERDUE)

"""The killer feature, as pure logic: outstanding receivables + AR aging.

The Lexware API answers per-invoice and refuses the aggregate. This module turns a
stream of `voucherlist` rows — which already carry `openAmount`, `dueDate`,
`voucherStatus` and `contactName` (no per-invoice GET needed) — into the answer a
business actually asks: *who owes me money, how overdue, and who do I chase?*

Rules encoded here were verified live against the sandbox:
- Sum **`openAmount`**, never `totalAmount` — a partial payment lowers the balance
  while the invoice may still be overdue (status and balance are independent).
- Aging buckets are computed from `dueDate` vs today (the API has no buckets).
- `overdue` is only a voucherlist-derived status; a row's `openAmount > 0` with a
  past `dueDate` is what actually makes it overdue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

# The classic AR aging ladder.
BUCKETS = ("current", "1-30", "31-60", "61-90", "90+")


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def days_overdue(due: str | None, today: date) -> int:
    d = _parse_date(due)
    if d is None:
        return 0
    return (today - d).days


def bucket_for(days: int) -> str:
    if days <= 0:
        return "current"
    if days <= 30:
        return "1-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


@dataclass
class Row:
    """One outstanding invoice, enriched with aging."""

    voucherNumber: str | None
    contactId: str | None
    contactName: str
    dueDate: str | None
    openAmount: float
    currency: str
    daysOverdue: int
    bucket: str
    voucherStatus: str
    voucherNumber_id: str | None = None


def enrich(voucherlist_rows, today: date | None = None) -> list[Row]:
    """Turn raw voucherlist rows into aging-enriched Rows (only those still owing)."""
    today = today or date.today()
    out: list[Row] = []
    for v in voucherlist_rows:
        open_amt = float(v.get("openAmount") or 0)
        if open_amt <= 0:
            continue  # nothing owed — not a receivable
        d = days_overdue(v.get("dueDate"), today)
        out.append(
            Row(
                voucherNumber=v.get("voucherNumber"),
                voucherNumber_id=v.get("id"),
                contactId=v.get("contactId"),
                contactName=v.get("contactName") or "",
                dueDate=v.get("dueDate"),
                openAmount=round(open_amt, 2),
                currency=v.get("currency") or "EUR",
                daysOverdue=max(0, d),
                bucket=bucket_for(d),
                voucherStatus=v.get("voucherStatus") or "",
            )
        )
    return out


@dataclass
class Aging:
    total: float = 0.0
    overdue: float = 0.0
    currency: str = "EUR"
    count: int = 0
    overdueCount: int = 0
    buckets: dict = field(default_factory=lambda: {b: 0.0 for b in BUCKETS})
    bucketCounts: dict = field(default_factory=lambda: {b: 0 for b in BUCKETS})


def summarise(rows: list[Row]) -> Aging:
    """The headline totals + the aging ladder."""
    a = Aging()
    for r in rows:
        a.total = round(a.total + r.openAmount, 2)
        a.count += 1
        a.buckets[r.bucket] = round(a.buckets[r.bucket] + r.openAmount, 2)
        a.bucketCounts[r.bucket] += 1
        if r.currency:
            a.currency = r.currency
        if r.daysOverdue > 0:
            a.overdue = round(a.overdue + r.openAmount, 2)
            a.overdueCount += 1
    return a


def by_customer(rows: list[Row]) -> list[dict]:
    """Per-customer rollup, worst (most overdue owed) first."""
    agg: dict[str, dict] = {}
    for r in rows:
        key = r.contactId or r.contactName or "(unknown)"
        c = agg.setdefault(
            key,
            {"contactId": r.contactId, "contactName": r.contactName, "open": 0.0, "overdue": 0.0, "count": 0, "currency": r.currency, "maxDaysOverdue": 0},
        )
        c["open"] = round(c["open"] + r.openAmount, 2)
        c["count"] += 1
        c["maxDaysOverdue"] = max(c["maxDaysOverdue"], r.daysOverdue)
        if r.daysOverdue > 0:
            c["overdue"] = round(c["overdue"] + r.openAmount, 2)
    return sorted(agg.values(), key=lambda c: (-c["overdue"], -c["open"]))


def dunning_candidates(rows: list[Row], min_days: int = 1) -> list[Row]:
    """Overdue invoices worth chasing — the "who do I dun?" list, worst first."""
    cand = [r for r in rows if r.daysOverdue >= min_days]
    return sorted(cand, key=lambda r: (-r.daysOverdue, -r.openAmount))

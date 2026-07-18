"""Receivables / AR aging — pure logic, hermetic. The killer feature's heart.

Every rule here was verified live against the sandbox; these lock it in.
"""

from __future__ import annotations

from datetime import date

import pytest

from lexwarecli.receivables import (
    bucket_for,
    by_customer,
    days_overdue,
    dunning_candidates,
    enrich,
    summarise,
)

TODAY = date(2026, 7, 18)


def row(number, contact, contactName, due, open_, status="open", currency="EUR", id_=None):
    return {
        "id": id_ or number,
        "voucherNumber": number,
        "contactId": contact,
        "contactName": contactName,
        "dueDate": f"{due}T00:00:00.000+02:00" if due else None,
        "openAmount": open_,
        "voucherStatus": status,
        "currency": currency,
    }


# ---- aging math ------------------------------------------------------

@pytest.mark.parametrize("days,bucket", [
    (-5, "current"), (0, "current"), (1, "1-30"), (30, "1-30"),
    (31, "31-60"), (60, "31-60"), (61, "61-90"), (90, "61-90"), (91, "90+"), (365, "90+"),
])
def test_bucket_ladder(days, bucket):
    assert bucket_for(days) == bucket


def test_days_overdue_from_due_date():
    assert days_overdue("2026-07-03T00:00:00.000+02:00", TODAY) == 15
    assert days_overdue("2026-08-01T00:00:00.000+02:00", TODAY) == -14  # not yet due
    assert days_overdue(None, TODAY) == 0


# ---- enrich: only real receivables -----------------------------------

def test_enrich_drops_fully_paid_rows():
    """openAmount 0 is not a receivable, whatever the status says."""
    rows = enrich([row("RE1", "c", "A", "2026-06-01", 0.0, status="paid")], TODAY)
    assert rows == []


def test_enrich_keeps_partially_paid_overdue():
    """THE subtlety: a partial payment lowers openAmount but the invoice is still
    overdue. We age on the due date and owe the openAmount, independently."""
    rows = enrich([row("RE1", "c", "A", "2026-06-02", 437.50, status="overdue")], TODAY)
    assert len(rows) == 1
    assert rows[0].openAmount == 437.50   # what's owed, not the total
    assert rows[0].daysOverdue == 46
    assert rows[0].bucket == "31-60"


def test_enrich_current_invoice_is_not_overdue():
    rows = enrich([row("RE1", "c", "A", "2026-07-27", 2975.0)], TODAY)
    assert rows[0].daysOverdue == 0
    assert rows[0].bucket == "current"


# ---- summarise -------------------------------------------------------

def _sample():
    return enrich([
        row("RE1", "c1", "Alpha GmbH", "2026-07-27", 2975.0),   # current
        row("RE2", "c2", "Beta UG",    "2026-07-03", 535.50, status="overdue"),  # 15d -> 1-30
        row("RE3", "c1", "Alpha GmbH", "2026-06-02", 1428.0, status="overdue"),  # 46d -> 31-60
        row("RE4", "c3", "Gamma AG",   "2026-04-14", 1166.20, status="overdue"), # 95d -> 90+
        row("RE5", "c1", "Alpha GmbH", "2026-06-01", 0.0, status="paid"),        # dropped
    ], TODAY)


def test_summarise_totals_and_overdue():
    a = summarise(_sample())
    assert a.count == 4                      # paid one dropped
    assert a.total == 6104.70
    assert a.overdue == 3129.70              # everything but the current one
    assert a.overdueCount == 3
    assert a.currency == "EUR"


def test_summarise_bucket_ladder():
    a = summarise(_sample())
    assert a.buckets == {"current": 2975.0, "1-30": 535.50, "31-60": 1428.0, "61-90": 0.0, "90+": 1166.20}
    assert a.bucketCounts == {"current": 1, "1-30": 1, "31-60": 1, "61-90": 0, "90+": 1}


# ---- per-customer ----------------------------------------------------

def test_by_customer_rolls_up_and_sorts_worst_first():
    cust = by_customer(_sample())
    # Alpha has the most overdue owed (1428) -> first; sorted by overdue desc.
    assert cust[0]["contactName"] == "Alpha GmbH"
    alpha = next(c for c in cust if c["contactName"] == "Alpha GmbH")
    assert alpha["open"] == 4403.0           # 2975 current + 1428 overdue
    assert alpha["overdue"] == 1428.0
    assert alpha["count"] == 2
    assert alpha["maxDaysOverdue"] == 46


# ---- dunning ---------------------------------------------------------

def test_dunning_candidates_are_overdue_only_worst_first():
    cands = dunning_candidates(_sample())
    assert [r.voucherNumber for r in cands] == ["RE4", "RE3", "RE2"]  # 95, 46, 15 days
    assert all(r.daysOverdue > 0 for r in cands)


def test_dunning_min_days_filters():
    cands = dunning_candidates(_sample(), min_days=30)
    assert [r.voucherNumber for r in cands] == ["RE4", "RE3"]  # only >=30 days


def test_empty_input_is_zeroes_not_a_crash():
    a = summarise([])
    assert a.total == 0.0 and a.count == 0 and a.overdue == 0.0
    assert by_customer([]) == []
    assert dunning_candidates([]) == []

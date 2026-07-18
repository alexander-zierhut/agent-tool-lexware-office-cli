"""Integration tests — the CLI's client against the booted mock backend.

These prove the whole stack (client -> rate limiter -> mock -> domain) behaves
like the real API. The mock replaces the "no test instance" gap: a real server the
tests boot, not canned fixtures.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from lexwareoffice.errors import ConflictError, NotFoundError, ValidationError
from lexwareoffice.receivables import enrich, summarise

pytestmark = pytest.mark.integration


def _company(client, name):
    r = client.post("/contacts", json={"version": 0, "roles": {"customer": {}}, "company": {"name": name}})
    return r["id"]


def _invoice(client, contact_id, days_ago, net, finalize=True):
    d = (date(2026, 7, 18) - timedelta(days=days_ago)).isoformat() + "T00:00:00.000+02:00"
    body = {
        "voucherDate": d,
        "address": {"contactId": contact_id},
        "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": d},
        "paymentConditions": {"paymentTermLabel": "14 Tage", "paymentTermDuration": 14},
        "lineItems": [{"type": "custom", "name": "Leistung", "quantity": 1, "unitName": "St", "unitPrice": {"currency": "EUR", "netAmount": net, "taxRatePercentage": 19}}],
        "totalPrice": {"currency": "EUR"},
    }
    return client.post("/invoices", json=body, params={"finalize": "true"} if finalize else None)


def test_profile_reachable(client):
    p = client.profile()
    assert "businessFeatures" in p and p.get("organizationId")


def test_contact_create_returns_action_result_then_get_reveals_number(client):
    r = _company(client, "Integration GmbH")
    # POST returned an action-result-shaped dict; GET reveals the assigned number
    c = client.get(f"/contacts/{r}")
    assert "createdDate" not in c  # object carries no timestamps
    assert c["roles"]["customer"]["number"] >= 10000


def test_stale_version_is_a_conflict(client):
    cid = _company(client, "Lock GmbH")
    cur = client.get(f"/contacts/{cid}")
    cur["version"] = 999
    with pytest.raises(ConflictError):
        client.put(f"/contacts/{cid}", json=cur)


def test_pagination_stops_on_last(client):
    for i in range(7):
        _company(client, f"Page Co {i}")
    got = list(client.paginate("/contacts", size=3))
    assert len(got) >= 7  # includes the ones this test made + any prior


def test_voucherlist_requires_a_status(client):
    with pytest.raises(ValidationError):
        client.get("/voucherlist", params={"voucherType": "invoice"})


def test_overdue_is_a_subset_of_open(client):
    cid = _company(client, "Overdue GmbH")
    _invoice(client, cid, days_ago=60, net=1000)   # overdue
    _invoice(client, cid, days_ago=0, net=500)     # current
    open_rows = list(client.paginate("/voucherlist", params={"voucherType": "invoice", "voucherStatus": "open"}))
    overdue_rows = list(client.paginate("/voucherlist", params={"voucherType": "invoice", "voucherStatus": "overdue"}))
    statuses = {r["voucherStatus"] for r in open_rows}
    assert "overdue" in statuses  # open includes overdue rows, shown as overdue
    assert all(r["voucherStatus"] == "overdue" for r in overdue_rows)
    assert len(overdue_rows) < len(open_rows)


def test_receivables_end_to_end_partial_payment(client):
    """The killer feature over the wire: a partial payment lowers openAmount but
    the invoice stays overdue, and the aging reflects openAmount."""
    cid = _company(client, "AR GmbH")
    inv = _invoice(client, cid, days_ago=50, net=1000)  # gross 1190, ~36d overdue
    client.post(f"/__mock__/vouchers/{inv['id']}/pay", json={"amount": 190})  # partial
    rows_raw = {v["id"]: v for v in client.paginate("/voucherlist", params={"voucherType": "invoice", "voucherStatus": "open"})}
    rows = enrich(rows_raw.values(), today=date(2026, 7, 18))
    mine = next(r for r in rows if r.contactName == "AR GmbH")
    assert mine.openAmount == 1000.0        # 1190 - 190 partial
    assert mine.daysOverdue > 0             # still overdue despite the payment
    a = summarise(rows)
    assert a.overdue >= 1000.0


def test_pdf_only_for_finalized(client):
    cid = _company(client, "PDF GmbH")
    draft = _invoice(client, cid, days_ago=0, net=100, finalize=False)
    with pytest.raises(ConflictError):  # draft cannot render
        client.get(f"/invoices/{draft['id']}/file", raw=True, accept="application/pdf")
    final = _invoice(client, cid, days_ago=0, net=100, finalize=True)
    # With Accept: application/pdf the server hands back RAW bytes.
    pdf = client.get(f"/invoices/{final['id']}/file", raw=True, accept="application/pdf")
    assert isinstance(pdf, (bytes, bytearray)) and pdf[:5] == b"%PDF-"
    # But with the client's DEFAULT Accept: application/json, Lexware (and now the
    # mock) base64-encodes the PDF — the trap the `invoice pdf` command must dodge.
    b64 = client.get(f"/invoices/{final['id']}/file", raw=True)
    assert isinstance(b64, (bytes, bytearray)) and b64[:5] != b"%PDF-"
    from lexwareoffice.commands.invoice import _as_pdf_bytes
    assert _as_pdf_bytes(b64)[:5] == b"%PDF-"  # …and the helper recovers it


def test_missing_resource_is_not_found(client):
    with pytest.raises(NotFoundError):
        client.get("/invoices/00000000-0000-0000-0000-000000000000")


def test_the_client_paces_itself_under_the_real_limit(mock_server):
    """With the mock's limiter ON (2/s), the CLI's own token bucket must keep a
    burst clean — proving the pacing works against a real 429-ing server."""
    import os
    import subprocess
    import time
    import urllib.request
    from pathlib import Path

    # boot a second mock instance WITH the limiter on
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    mock_dir = Path(__file__).resolve().parents[2] / "lexware-office-mock"
    proc = subprocess.Popen(["node", "src/server.js"], cwd=str(mock_dir),
                            env={**os.environ, "PORT": str(port), "MOCK_RATE_RPS": "2", "MOCK_RATE_BURST": "2"},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{base}/__mock__/health", timeout=1); break
            except Exception:
                time.sleep(0.1)
        from lexwareoffice.client import Client
        c = Client(base, "k")  # default rate 1.3, burst 1
        codes_ok = 0
        for _ in range(8):
            c.profile()  # each request paced by the client's bucket
            codes_ok += 1
        c.close()
        assert codes_ok == 8  # no RateLimited raised -> the client stayed under the ceiling
    finally:
        proc.terminate()

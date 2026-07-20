"""CLI-level tests for `create --from` (finalize by recreation) and sales-doc PDF.

These invoke the real `lexware-office` command as a subprocess against the booted
mock, so the whole surface is exercised: option parsing, the recreate helper, exit
codes, and the JSON-on-stdout / error-on-stderr contract. Setup (creating the source
draft) uses the in-process Client fixture for speed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration

_D = "2026-07-20T00:00:00.000+02:00"


def _run(base, args, tmp_path):
    env = {
        **os.environ,
        "LEXWARE_URL": base,
        "LEXWARE_API_KEY": "cli-test",
        "LEXWAREOFFICE_CLI_FORMAT": "json",
        "LEXWAREOFFICE_CONFIG_DIR": str(tmp_path / "cfg"),
        "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Keyring",
        "CI": "true",  # never prompt
    }
    return subprocess.run(
        [sys.executable, "-m", "lexwareoffice", *args],
        capture_output=True, text=True, env=env,
    )


def _company(client, name):
    return client.post("/contacts", json={"version": 0, "roles": {"customer": {}}, "company": {"name": name}})["id"]


def _rich_quotation_draft(client, cid):
    """A multi-line-item draft with intro/remark/title — the issue's core case."""
    return client.post("/quotations", json={
        "voucherDate": _D,
        "address": {"contactId": cid},
        "title": "Unser Angebot",
        "introduction": "Danke fuer die Anfrage.",
        "remark": "30 Tage gueltig.",
        "expirationDate": "2026-08-31T00:00:00.000+02:00",
        "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": _D},
        "totalPrice": {"currency": "EUR"},
        "lineItems": [
            {"type": "custom", "name": "Beratung", "quantity": 10, "unitName": "Stunde",
             "unitPrice": {"currency": "EUR", "netAmount": 100, "taxRatePercentage": 19}},
            {"type": "custom", "name": "Handbuch", "quantity": 5, "unitName": "Stueck",
             "unitPrice": {"currency": "EUR", "netAmount": 10, "taxRatePercentage": 7}},
        ],
    })["id"]


def test_create_from_finalize_recreates_full_content(client, mock_server, tmp_path):
    cid = _company(client, "FromFinalize GmbH")
    draft = _rich_quotation_draft(client, cid)
    src = client.get(f"/quotations/{draft}")

    r = _run(mock_server, ["quotation", "create", "--from", draft, "--finalize"], tmp_path)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["from"] == draft
    assert out["finalized"] is True
    assert "note" in out and draft in out["note"]

    new = client.get(f"/quotations/{out['id']}")
    assert new["voucherStatus"] == "open"          # issued
    assert new["voucherNumber"]                    # numbered
    assert new["id"] != draft                      # a NEW document
    # ALL line items + intro/remark/title preserved (the issue's requirement)
    assert [li["name"] for li in new["lineItems"]] == ["Beratung", "Handbuch"]
    assert new["title"] == "Unser Angebot"
    assert new["introduction"].startswith("Danke")
    assert new["remark"].startswith("30 Tage")
    # totals preserved 1:1
    assert new["totalPrice"]["totalGrossAmount"] == src["totalPrice"]["totalGrossAmount"]


def test_create_from_without_finalize_is_a_draft_clone(client, mock_server, tmp_path):
    cid = _company(client, "Clone GmbH")
    draft = _rich_quotation_draft(client, cid)
    r = _run(mock_server, ["quotation", "create", "--from", draft], tmp_path)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["finalized"] is False
    assert out["version"] == 0                      # a fresh draft copy
    new = client.get(f"/quotations/{out['id']}")
    assert new["voucherStatus"] == "draft"
    assert new["voucherNumber"] is None
    assert len(new["lineItems"]) == 2


def test_pdf_of_recreated_quotation_writes_pdf_bytes(client, mock_server, tmp_path):
    cid = _company(client, "PdfQuote GmbH")
    draft = _rich_quotation_draft(client, cid)
    new_id = json.loads(
        _run(mock_server, ["quotation", "create", "--from", draft, "--finalize"], tmp_path).stdout
    )["id"]
    out_pdf = tmp_path / "q.pdf"
    r = _run(mock_server, ["quotation", "pdf", new_id, "--out", str(out_pdf)], tmp_path)
    assert r.returncode == 0, r.stderr
    assert out_pdf.exists()
    assert out_pdf.read_bytes()[:5] == b"%PDF-"


def test_pdf_of_draft_exits_6_with_create_from_message(client, mock_server, tmp_path):
    cid = _company(client, "DraftPdf GmbH")
    draft = _rich_quotation_draft(client, cid)
    r = _run(mock_server, ["quotation", "pdf", draft, "--out", str(tmp_path / "x.pdf")], tmp_path)
    assert r.returncode == 6
    assert "create --from" in r.stderr
    assert not (tmp_path / "x.pdf").exists()


def test_from_and_contact_are_mutually_exclusive_exit_7(client, mock_server, tmp_path):
    cid = _company(client, "Excl GmbH")
    draft = _rich_quotation_draft(client, cid)
    r = _run(mock_server, ["quotation", "create", "--from", draft, "--contact", "x"], tmp_path)
    assert r.returncode == 7
    assert "not both" in r.stderr


def test_create_with_neither_from_nor_contact_exits_7(mock_server, tmp_path):
    r = _run(mock_server, ["quotation", "create"], tmp_path)
    assert r.returncode == 7


def test_bad_from_id_exits_5_not_found(mock_server, tmp_path):
    r = _run(mock_server, ["quotation", "create", "--from",
                           "00000000-0000-0000-0000-000000000000", "--finalize"], tmp_path)
    assert r.returncode == 5


def test_delivery_note_from_drops_prices(client, mock_server, tmp_path):
    cid = _company(client, "DN From GmbH")
    draft = client.post("/delivery-notes", json={
        "voucherDate": _D,
        "address": {"contactId": cid},
        "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": _D},
        "lineItems": [
            {"type": "custom", "name": "Ware A", "quantity": 3, "unitName": "Stueck"},
            {"type": "custom", "name": "Ware B", "quantity": 7, "unitName": "Karton"},
        ],
    })["id"]
    r = _run(mock_server, ["delivery-note", "create", "--from", draft, "--finalize"], tmp_path)
    assert r.returncode == 0, r.stderr
    new = client.get(f"/delivery-notes/{json.loads(r.stdout)['id']}")
    assert new["voucherStatus"] == "open"
    assert len(new["lineItems"]) == 2
    assert all("unitPrice" not in li for li in new["lineItems"])
    assert "totalPrice" not in new


def test_dunning_from_finalize_stays_draft_keeps_preceding(client, mock_server, tmp_path):
    cid = _company(client, "Dun From GmbH")
    # a finalized invoice to act as the preceding voucher
    inv = client.post("/invoices", params={"finalize": "true"}, json={
        "voucherDate": _D, "address": {"contactId": cid}, "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": _D},
        "paymentConditions": {"paymentTermLabel": "14", "paymentTermDuration": 14},
        "lineItems": [{"type": "custom", "name": "L", "quantity": 1, "unitName": "St",
                       "unitPrice": {"currency": "EUR", "netAmount": 1000, "taxRatePercentage": 19}}],
        "totalPrice": {"currency": "EUR"}})["id"]
    draft = client.post("/dunnings", params={"precedingSalesVoucherId": inv}, json={
        "voucherDate": _D, "address": {"contactId": cid}, "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": _D},
        "totalPrice": {"currency": "EUR"},
        "lineItems": [{"type": "custom", "name": "Mahngebuehr", "quantity": 1, "unitName": "St",
                       "unitPrice": {"currency": "EUR", "netAmount": 5, "taxRatePercentage": 19}}]})["id"]
    r = _run(mock_server, ["dunning", "create", "--from", draft, "--finalize"], tmp_path)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["finalized"] is False                # dunnings never finalize
    new = client.get(f"/dunnings/{out['id']}")
    assert new["voucherStatus"] == "draft"
    assert new["voucherNumber"] is None
    assert new["relatedVouchers"][0]["id"] == inv   # preceding link carried


def test_invoice_create_from_finalize_recreates(client, mock_server, tmp_path):
    cid = _company(client, "InvFrom GmbH")
    draft = client.post("/invoices", json={
        "voucherDate": _D, "address": {"contactId": cid}, "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": _D},
        "paymentConditions": {"paymentTermLabel": "14 Tage", "paymentTermDuration": 14},
        "lineItems": [{"type": "custom", "name": "Beratung", "quantity": 8, "unitName": "Stunde",
                       "unitPrice": {"currency": "EUR", "netAmount": 100, "taxRatePercentage": 19}}],
        "totalPrice": {"currency": "EUR"}})["id"]
    src = client.get(f"/invoices/{draft}")
    r = _run(mock_server, ["invoice", "create", "--from", draft, "--finalize"], tmp_path)
    assert r.returncode == 0, r.stderr
    new = client.get(f"/invoices/{json.loads(r.stdout)['id']}")
    assert new["voucherStatus"] == "open"
    assert new["voucherNumber"].startswith("RE")
    assert new["totalPrice"]["totalGrossAmount"] == src["totalPrice"]["totalGrossAmount"]
    assert new["dueDate"]                            # paymentConditions preserved -> due date


def test_invoice_finalize_stub_steers_to_create_from(client, mock_server, tmp_path):
    cid = _company(client, "InvFinStub GmbH")
    draft = client.post("/invoices", json={
        "voucherDate": _D, "address": {"contactId": cid}, "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": _D},
        "lineItems": [{"type": "custom", "name": "L", "quantity": 1, "unitName": "St",
                       "unitPrice": {"currency": "EUR", "netAmount": 10, "taxRatePercentage": 19}}],
        "totalPrice": {"currency": "EUR"}})["id"]
    r = _run(mock_server, ["invoice", "finalize", draft], tmp_path)
    assert r.returncode == 7
    assert "create --from" in r.stderr

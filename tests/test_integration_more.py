"""Integration tests for the rest of the command surface, against the mock."""

from __future__ import annotations

import pytest

from lexwarecli.errors import ValidationError

pytestmark = pytest.mark.integration


def _company(client, name):
    return client.post("/contacts", json={"version": 0, "roles": {"customer": {}}, "company": {"name": name}})["id"]


# ---- webhooks (the requested feature) --------------------------------

def test_webhook_subscribe_list_get_delete(client):
    sub = client.post("/event-subscriptions", json={"eventType": "invoice.created", "callbackUrl": "https://example.test/hook"})
    sid = sub.get("subscriptionId") or sub.get("id")
    assert sid

    listing = client.get("/event-subscriptions")
    rows = listing.get("content", listing) if isinstance(listing, dict) else listing
    assert any((r.get("subscriptionId") or r.get("id")) == sid for r in rows)

    one = client.get(f"/event-subscriptions/{sid}")
    assert (one.get("eventType") or "") == "invoice.created"

    client.delete(f"/event-subscriptions/{sid}")  # 204, no raise


# ---- articles --------------------------------------------------------

def test_article_create_bad_type_is_validation_error(client):
    with pytest.raises(ValidationError):
        client.post("/articles", json={"title": "X", "type": "product", "unitName": "St", "price": {"netPrice": 10, "leadingPrice": "NET", "taxRate": 19}})


def test_article_create_and_list(client):
    r = client.post("/articles", json={"title": "Beratungsstunde", "type": "SERVICE", "unitName": "Stunde", "price": {"netPrice": 120, "leadingPrice": "NET", "taxRate": 19}})
    assert r.get("id")
    arts = list(client.paginate("/articles"))
    assert any(a.get("title") == "Beratungsstunde" for a in arts)


# ---- other sales documents ------------------------------------------

def test_quotation_create_and_get(client):
    cid = _company(client, "Quote GmbH")
    q = client.post("/quotations", json={
        "voucherDate": "2026-07-18T00:00:00.000+02:00",
        "address": {"contactId": cid},
        "lineItems": [{"type": "custom", "name": "Angebot", "quantity": 1, "unitName": "Pauschale", "unitPrice": {"currency": "EUR", "netAmount": 5000, "taxRatePercentage": 19}}],
        "totalPrice": {"currency": "EUR"}, "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": "2026-07-18T00:00:00.000+02:00"},
    })
    got = client.get(f"/quotations/{q['id']}")
    assert got["voucherType"] == "quotation"
    assert got["voucherStatus"] == "draft"


def test_credit_note_pursues_an_invoice(client):
    cid = _company(client, "Credit GmbH")
    d = "2026-07-18T00:00:00.000+02:00"
    inv = client.post("/invoices", params={"finalize": "true"}, json={
        "voucherDate": d, "address": {"contactId": cid}, "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": d},
        "paymentConditions": {"paymentTermLabel": "14", "paymentTermDuration": 14},
        "lineItems": [{"type": "custom", "name": "L", "quantity": 1, "unitName": "St", "unitPrice": {"currency": "EUR", "netAmount": 100, "taxRatePercentage": 19}}],
        "totalPrice": {"currency": "EUR"}})
    cn = client.post("/credit-notes", params={"precedingSalesVoucherId": inv["id"]}, json={
        "voucherDate": d, "address": {"contactId": cid}, "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": d},
        "lineItems": [{"type": "custom", "name": "Gutschrift", "quantity": 1, "unitName": "St", "unitPrice": {"currency": "EUR", "netAmount": 50, "taxRatePercentage": 19}}],
        "totalPrice": {"currency": "EUR"}})
    got = client.get(f"/credit-notes/{cn['id']}")
    assert got["voucherType"] == "creditNote"
    assert got["relatedVouchers"] and got["relatedVouchers"][0]["id"] == inv["id"]


def test_dunning_requires_a_preceding(client):
    cid = _company(client, "Dun GmbH")
    d = "2026-07-18T00:00:00.000+02:00"
    with pytest.raises(Exception):  # 400/406 — missing preceding
        client.post("/dunnings", json={"voucherDate": d, "address": {"contactId": cid}, "taxConditions": {"taxType": "net"}, "lineItems": [], "totalPrice": {"currency": "EUR"}, "shippingConditions": {"shippingType": "none", "shippingDate": d}})


# ---- reference data + payments --------------------------------------

def test_reference_data(client):
    countries = client.get("/countries")
    assert isinstance(countries, list) and any(c["countryCode"] == "DE" for c in countries)
    assert isinstance(client.get("/posting-categories"), list)
    assert isinstance(client.get("/payment-conditions"), list)


def test_invoice_payments_shape(client):
    cid = _company(client, "Pay GmbH")
    d = "2026-06-01T00:00:00.000+02:00"
    inv = client.post("/invoices", params={"finalize": "true"}, json={
        "voucherDate": d, "address": {"contactId": cid}, "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "none", "shippingDate": d},
        "paymentConditions": {"paymentTermLabel": "14", "paymentTermDuration": 14},
        "lineItems": [{"type": "custom", "name": "L", "quantity": 1, "unitName": "St", "unitPrice": {"currency": "EUR", "netAmount": 1000, "taxRatePercentage": 19}}],
        "totalPrice": {"currency": "EUR"}})
    client.post(f"/__mock__/vouchers/{inv['id']}/pay", json={"amount": 500})
    pay = client.get(f"/payments/{inv['id']}")
    assert pay["paymentStatus"] == "openRevenue"   # partly paid -> still open
    assert pay["openAmount"] == 690.0              # 1190 - 500
    assert pay["voucherStatus"] == "open"          # never 'overdue' here
    assert len(pay["paymentItems"]) == 1

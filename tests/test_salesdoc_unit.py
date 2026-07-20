"""Hermetic unit tests for the sales-doc recreate helper (no network).

`recreate_body_from` is the core of `create --from`: it turns a fetched document
into a clean create body by stripping the read-only/computed fields the API refuses
on write, while preserving the full content and the preceding link.
"""

from __future__ import annotations

from lexwareoffice.commands._shared import recreate_body_from

# A GET-shaped sales document as the API returns it: full content plus the
# read-only/computed fields (id, version, number, status, timestamps, taxAmounts,
# per-line lineItemAmount, computed unitPrice.grossAmount, relatedVouchers, ...).
_DOC = {
    "id": "src-id-123",
    "organizationId": "org-1",
    "version": 3,
    "voucherStatus": "draft",
    "voucherNumber": None,
    "voucherType": "quotation",
    "createdDate": "2026-07-01T00:00:00.000+02:00",
    "updatedDate": "2026-07-02T00:00:00.000+02:00",
    "dueDate": "2026-08-03T00:00:00.000+02:00",
    "archived": False,
    "electronicDocumentProfile": "NONE",
    "voucherDate": "2026-07-01T00:00:00.000+02:00",
    "expirationDate": "2026-08-31T00:00:00.000+02:00",
    "title": "Unser Angebot",
    "introduction": "Danke fuer die Anfrage.",
    "remark": "30 Tage gueltig.",
    "address": {"contactId": "c-1", "name": "Muster GmbH"},
    "taxConditions": {"taxType": "net"},
    "shippingConditions": {"shippingType": "none", "shippingDate": "2026-07-01T00:00:00.000+02:00"},
    "lineItems": [
        {"id": "li-1", "type": "custom", "name": "Beratung", "quantity": 10, "unitName": "Stunde",
         "unitPrice": {"currency": "EUR", "netAmount": 100, "grossAmount": 119, "taxRatePercentage": 19},
         "lineItemAmount": 1000},
        {"id": "li-2", "type": "custom", "name": "Handbuch", "quantity": 5, "unitName": "Stueck",
         "unitPrice": {"currency": "EUR", "netAmount": 10, "grossAmount": 10.7, "taxRatePercentage": 7},
         "lineItemAmount": 50},
    ],
    "totalPrice": {"currency": "EUR", "totalNetAmount": 1050, "totalGrossAmount": 1243.5, "totalTaxAmount": 193.5},
    "taxAmounts": [{"taxRatePercentage": 19, "taxAmount": 190, "netAmount": 1000}],
    "files": {"documentFileId": "f-1"},
    "relatedVouchers": [{"id": "prev-1", "voucherType": "invoice", "voucherNumber": "RE0001"}],
}

_STRIPPED = {
    "id", "version", "voucherNumber", "voucherStatus", "voucherType", "createdDate",
    "updatedDate", "dueDate", "files", "organizationId", "taxAmounts", "archived",
    "electronicDocumentProfile", "relatedVouchers",
}


def test_strips_all_read_only_top_level_fields():
    body, preceding = recreate_body_from(_DOC, money=True)
    for k in _STRIPPED:
        assert k not in body, f"{k} must be stripped"
    # content is preserved
    assert body["title"] == "Unser Angebot"
    assert body["introduction"].startswith("Danke")
    assert body["remark"].startswith("30")
    assert body["expirationDate"] == "2026-08-31T00:00:00.000+02:00"
    assert body["voucherDate"] == "2026-07-01T00:00:00.000+02:00"
    assert body["address"] == {"contactId": "c-1", "name": "Muster GmbH"}


def test_preceding_id_extracted_from_related_vouchers():
    _, preceding = recreate_body_from(_DOC, money=True)
    assert preceding == "prev-1"


def test_line_items_lose_id_and_amount_but_keep_price_when_money():
    body, _ = recreate_body_from(_DOC, money=True)
    assert len(body["lineItems"]) == 2
    for li in body["lineItems"]:
        assert "id" not in li
        assert "lineItemAmount" not in li
        assert li["unitPrice"]["netAmount"] in (100, 10)  # prices kept for money types
    assert [li["name"] for li in body["lineItems"]] == ["Beratung", "Handbuch"]


def test_money_false_drops_unit_prices():
    body, _ = recreate_body_from(_DOC, money=False)
    for li in body["lineItems"]:
        assert "unitPrice" not in li, "delivery-note recreate must not carry prices"
        assert li["name"] and li["quantity"] and li["unitName"]  # name/qty/unit kept


def test_total_price_collapsed_to_currency_only():
    body, _ = recreate_body_from(_DOC, money=True)
    assert body["totalPrice"] == {"currency": "EUR"}


def test_total_price_preserves_discount_inputs_drops_computed_totals():
    # A draft with a total discount must keep the discount (a writable input) on
    # the reissue, or the finalized document over-bills. Computed totals are dropped.
    doc = {**_DOC, "totalPrice": {
        "currency": "EUR", "totalNetAmount": 900, "totalGrossAmount": 1000,
        "totalTaxAmount": 100, "totalDiscountPercentage": 10,
    }}
    body, _ = recreate_body_from(doc, money=True)
    assert body["totalPrice"] == {"currency": "EUR", "totalDiscountPercentage": 10}


def test_no_related_vouchers_yields_none_preceding():
    doc = {k: v for k, v in _DOC.items() if k != "relatedVouchers"}
    _, preceding = recreate_body_from(doc, money=True)
    assert preceding is None


def test_does_not_mutate_the_source_document():
    import copy

    original = copy.deepcopy(_DOC)
    recreate_body_from(_DOC, money=False)  # money=False mutates line items if careless
    assert _DOC == original, "the source doc must not be mutated"

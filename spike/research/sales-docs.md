# Sales Documents (non-invoice) — Lexware Office API

Covers the five "other sales document" endpoints plus down-payment invoices:
**quotations, order-confirmations, delivery-notes, credit-notes, dunnings, down-payment-invoices**.
Source: the single static docs page `https://developers.lexware.io/docs/` (fetched 2026-07-18,
887 KB HTML). All JSON below is quoted VERBATIM from that page (real sample UUIDs, dates, enum
values). Base URL `https://api.lexware.io` (legacy `.com` until Dec 2025). Auth
`Authorization: Bearer <apiKey>`, `Content-Type`/`Accept: application/json`.

These six share the invoice's data model almost exactly (address, lineItems, unitPrice, totalPrice,
taxAmounts, taxConditions, paymentConditions, shippingConditions, relatedVouchers, files). This file
concentrates on **how each differs from an invoice** and on the **document-chain (pursue) semantics**,
which are the real reason to have a separate endpoint per type.

---

## Endpoints

`{id}` is a resource UUID. `[?finalize=true]` is optional and defaults to draft. Money/PDF endpoints
are identical in shape across types.

| METHOD | Path | Purpose | Notes / permissions |
|--------|------|---------|---------------------|
| POST | `/v1/quotations[?finalize=true]` | Create a quotation (draft, or finalized `open`) | Read+write. **Old API keys need re-generating** to gain quotation scope (endpoint added later). No "pursue" — quotation is the head of the chain. |
| GET | `/v1/quotations/{id}` | Retrieve a quotation | |
| GET | `/v1/quotations/{id}/document` | Render/trigger the PDF, returns `{documentFileId}` | Two-step: get id here, then download via Files endpoint. |
| GET | `/v1/quotations/{id}/file` | Download the quotation PDF (binary) | `Accept: */*`. Really the Files endpoint. |
| POST | `/v1/order-confirmations[?finalize=true]` | Create an order confirmation | Read+write. |
| POST | `/v1/order-confirmations?precedingSalesVoucherId={id}` | **Pursue** a preceding voucher (e.g. quotation) into an order confirmation | 406 if pursue invalid; 406 if quotation has alternative/optional line items. |
| GET | `/v1/order-confirmations/{id}` | Retrieve | |
| GET | `/v1/order-confirmations/{id}/document` | Render PDF → `{documentFileId}` | |
| GET | `/v1/order-confirmations/{id}/file` | Download PDF | |
| POST | `/v1/credit-notes[?finalize=true]` | Create a credit note (refund) | Read+write. May be standalone or reference an invoice. |
| POST | `/v1/credit-notes?precedingSalesVoucherId={id}[&finalize=true]` | **Pursue** an invoice into a credit note | 406 if invoice is `draft`; closing invoices cannot be pursued to a credit note; only one credit note per invoice. |
| GET | `/v1/credit-notes/{id}` | Retrieve | |
| GET | `/v1/credit-notes/{id}/document` | Render PDF → `{documentFileId}` | |
| GET | `/v1/credit-notes/{id}/file` | Download PDF | |
| POST | `/v1/delivery-notes[?finalize=true]` | Create a delivery note | Read+write. **No prices/tax/payment** in the printed doc. |
| POST | `/v1/delivery-notes?precedingSalesVoucherId={id}` | **Pursue** a preceding voucher into a delivery note | 406 if quotation has alternative/optional items; 406 if referenced order-confirmation is `draft`. |
| GET | `/v1/delivery-notes/{id}` | Retrieve | |
| GET | `/v1/delivery-notes/{id}/document` | Render PDF → `{documentFileId}` | |
| GET | `/v1/delivery-notes/{id}/file` | Download PDF | |
| POST | `/v1/dunnings?precedingSalesVoucherId={id}` | Create a dunning (payment reminder) | **`precedingSalesVoucherId` is MANDATORY** — a dunning always references an invoice (or down-payment invoice). Always `draft`, **no `finalize`**. |
| GET | `/v1/dunnings/{id}` | Retrieve | |
| GET | `/v1/dunnings/{id}/document` | Render PDF → `{documentFileId}` | |
| GET | `/v1/dunnings/{id}/file` | Download PDF | |
| GET | `/v1/down-payment-invoices/{id}` | Retrieve | **READ-ONLY.** No create/update and no `/document` render endpoint. It *does* have a deeplink, but on the `/permalink/invoices/` path (see below). |
| GET | `/v1/down-payment-invoices/{id}/file` | Download PDF | |

Deeplinks (open in the Lexware web app, `{appbaseurl}` = `https://app.lexware.de`):
`{appbaseurl}/permalink/quotations/view/{id}` (and `/edit/{id}`), likewise `order-confirmations`,
`credit-notes`, `delivery-notes`, `dunnings`. **Down-payment invoices DO have a deeplink**, but it uses
the invoice path: `{appbaseurl}/permalink/invoices/view/{id}` and `/edit/{id}` (verbatim from the docs'
"Deeplink to a Down Payment Invoice" section). If a deeplink target id does not exist, Lexware redirects
to the main voucher list; if a doc is not editable, `edit` redirects to `view`.

There is **no list/GET-all endpoint** on any of these six. To enumerate them you must use the
**Voucherlist** endpoint (`GET /v1/voucherlist?voucherType=...`), which returns lightweight rows, then
fetch each by id here.

---

## Response examples

### Quotation — `GET /v1/quotations/424f784e-1f4e-439e-8f71-19673e6d6583`

```json
{
    "id": "424f784e-1f4e-439e-8f71-19673e6d6583",
    "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
    "createdDate": "2023-03-16T12:43:16.689+01:00",
    "updatedDate": "2023-03-16T15:26:30.074+01:00",
    "version": 4,
    "language": "de",
    "archived": false,
    "voucherStatus": "open",
    "voucherNumber": "AG0006",
    "voucherDate": "2023-03-16T12:43:03.900+01:00",
    "expirationDate": "2023-04-15T12:43:03.900+02:00",
    "address": {
        "contactId": "97c5794f-8ab2-43ad-b459-c5980b055e4d",
        "name": "Berliner Kindl GmbH",
        "street": "Jubiläumsweg 25",
        "city": "Berlin",
        "zip": "14089",
        "countryCode": "DE"
    },
    "lineItems": [
        {
            "id": "68569bfc-e5ae-472d-bbdf-6d51a82b1d2f",
            "type": "material",
            "name": "Axa Rahmenschloss Defender RL",
            "description": "Vollständig symmetrisches Design in metallicfarbener Ausführung. Der ergonomische Bedienkopf garantiert die große Benutzerfreundlichkeit dieses Schlosses. Sehr niedrige Kopfhöhe von 46 mm, also mehr Rahmenfreiheit... ",
            "quantity": 1,
            "unitName": "Stück",
            "unitPrice": {
                "currency": "EUR",
                "netAmount": 20.08,
                "grossAmount": 23.9,
                "taxRatePercentage": 19
            },
            "discountPercentage": 0,
            "lineItemAmount": 23.90,
            "subItems": [
                {
                    "id": "97b98491-e953-4dc9-97a9-ae437a8052b4",
                    "type": "material",
                    "name": "Abus Kabelschloss Primo 590 ",
                    "description": "- 9,5 mm starkes, smoke-mattes Spiralkabel mit integrierter Halterlösung zur Befestigung am Sattelklemmbolzen\n- bewährter Qualitäts-Schließzylinder mit praktischem Wendeschlüssel\n- KabelØ: 9,5 mm, Länge: 150 cm",
                    "quantity": 1,
                    "unitName": "Stück",
                    "unitPrice": {
                        "currency": "EUR",
                        "netAmount": 13.4,
                        "grossAmount": 15.95,
                        "taxRatePercentage": 19
                    },
                    "discountPercentage": 0,
                    "lineItemAmount": 15.95,
                    "alternative": true,
                    "optional": false
                }
            ],
            "alternative": false,
            "optional": false
        },
        {
            "id": "0722bcc6-d1b7-417b-b834-3b47794fa9ab",
            "type": "service",
            "name": "Einfache Montage",
            "description": "Aufwand für einfache Montagetätigkeit",
            "quantity": 1,
            "unitName": "Stunde",
            "unitPrice": {
                "currency": "EUR",
                "netAmount": 4.12,
                "grossAmount": 4.9,
                "taxRatePercentage": 19
            },
            "discountPercentage": 0,
            "lineItemAmount": 4.90,
            "alternative": false,
            "optional": true
        }
    ],
    "totalPrice": {
        "currency": "EUR",
        "totalNetAmount": 20.08,
        "totalGrossAmount": 23.90,
        "totalTaxAmount": 3.82
    },
    "taxAmounts": [
        {
            "taxRatePercentage": 19,
            "taxAmount": 3.82,
            "netAmount": 20.08
        }
    ],
    "taxConditions": {
        "taxType": "gross"
    },
    "paymentConditions": {
        "paymentTermLabel": "10 Tage - 3 %, 30 Tage netto",
        "paymentTermLabelTemplate": "{discountRange} Tage -{discount}, {paymentRange} Tage netto",
        "paymentTermDuration": 30,
        "paymentDiscountConditions": {
            "discountPercentage": 3,
            "discountRange": 10
        }
    },
    "introduction": "Gerne bieten wir Ihnen an:",
    "remark": "Wir freuen uns auf Ihre Auftragserteilung und sichern eine einwandfreie Ausführung zu.",
    "files": {
        "documentFileId": "ebd84e8a-716d-4a20-a76d-21de75a6d3d1"
    },
    "title": "Angebot"
}
```

Note: The "Properties" sample (not shown separately) is identical except it also carries
`"electronicDocumentProfile":"NONE"`, `"relatedVouchers": []` and
`"printLayoutId": "28c212c4-b6dd-11ee-b80a-dbc65f4ceccf"`. **Quotation-only fields vs an invoice:**
`expirationDate`, and line-item `alternative`/`optional`/`subItems`. A quotation has **no `dueDate`**,
no `shippingConditions` shown, and its `voucherStatus` enum is `draft | open | accepted | rejected`.

### Order Confirmation — `GET /v1/order-confirmations/e9066f04-8cc7-4616-93f8-ac9ecc8479c8`

```json
{
  "id": "e9066f04-8cc7-4616-93f8-ac9ecc8479c8",
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "createdDate": "2023-04-24T08:20:22.528+02:00",
  "updatedDate": "2023-04-24T08:20:22.528+02:00",
  "version": 0,
  "language": "de",
  "archived": false,
  "voucherStatus": "draft",
  "voucherNumber": "AB1019",
  "voucherDate": "2023-02-22T00:00:00.000+01:00",
  "address": {
    "name": "Bike & Ride GmbH & Co. KG",
    "supplement": "Gebäude 10",
    "street": "Musterstraße 42",
    "city": "Freiburg",
    "zip": "79112",
    "countryCode": "DE"
  },
  "lineItems": [
    {
      "id": "97b98491-e953-4dc9-97a9-ae437a8052b4",
      "type": "material",
      "name": "Abus Kabelschloss Primo 590 ",
      "description": "· 9,5 mm starkes, smoke-mattes Spiralkabel mit integrierter Halterlösung zur Befestigung am Sattelklemmbolzen · bewährter Qualitäts-Schließzylinder mit praktischem Wendeschlüssel · KabelØ: 9,5 mm, Länge: 150 cm",
      "quantity": 2,
      "unitName": "Stück",
      "unitPrice": {
        "currency": "EUR",
        "netAmount": 13.4,
        "grossAmount": 15.95,
        "taxRatePercentage": 19
      },
      "discountPercentage": 50,
      "lineItemAmount": 13.4
    },
    {
      "id": "dc4c805b-7df1-4310-a548-22be4499eb04",
      "type": "service",
      "name": "Aufwändige Montage",
      "description": "Aufwand für arbeitsintensive Montagetätigkeit",
      "quantity": 1,
      "unitName": "Stunde",
      "unitPrice": {
        "currency": "EUR",
        "netAmount": 8.32,
        "grossAmount": 8.9,
        "taxRatePercentage": 7
      },
      "discountPercentage": 0,
      "lineItemAmount": 8.32
    },
    {
      "type": "custom",
      "name": "Energieriegel Testpaket",
      "quantity": 1,
      "unitName": "Stück",
      "unitPrice": {
        "currency": "EUR",
        "netAmount": 5,
        "grossAmount": 5,
        "taxRatePercentage": 0
      },
      "discountPercentage": 0,
      "lineItemAmount": 5
    }
  ],
  "totalPrice": {
    "currency": "EUR",
    "totalNetAmount": 26.72,
    "totalGrossAmount": 29.85,
    "totalTaxAmount": 3.13
  },
  "taxAmounts": [
    {
      "taxRatePercentage": 0,
      "taxAmount": 0,
      "netAmount": 5
    },
    {
      "taxRatePercentage": 7,
      "taxAmount": 0.58,
      "netAmount": 8.32
    },
    {
      "taxRatePercentage": 19,
      "taxAmount": 2.55,
      "netAmount": 13.4
    }
  ],
  "taxConditions": {
    "taxType": "net"
  },
  "paymentConditions": {
    "paymentTermLabel": "10 Tage - 3 %, 30 Tage netto",
    "paymentTermLabelTemplate": "{discountRange} Tage -{discount}, {paymentRange} Tage netto",
    "paymentTermDuration": 30,
    "paymentDiscountConditions": {
      "discountPercentage": 3,
      "discountRange": 10
    }
  },
  "shippingConditions": {
    "shippingDate": "2023-04-22T00:00:00.000+02:00",
    "shippingType": "delivery"
  },
  "title": "Auftragsbestätigung",
  "introduction": "Ihre bestellten Positionen stellen wir Ihnen hiermit in Rechnung",
  "remark": "Vielen Dank für Ihren Einkauf",
  "deliveryTerms": "Lieferung an die angegebene Lieferadresse",
  "files": {
    "documentFileId": "023d5ef7-ad57-46d7-8579-9ffbdf218faf"
  }
}
```

Note: `version` is `0` here (freshly created draft — proves version starts at 0, not 1). The
"Properties" sample additionally shows `"totalDiscountAbsolute": null`, `"totalDiscountPercentage": null`
inside `totalPrice`, `"taxTypeNote": null` inside `taxConditions`, `"shippingEndDate": null`, and
`"contactId": null` in `address`. Order-confirmation-specific vs quotation: has `shippingConditions`
and `deliveryTerms`, **no `expirationDate`**, no `alternative`/`optional`/`subItems`. Status enum is
only `draft | open`.

### Credit Note — `GET /v1/credit-notes/e9066f04-8cc7-4616-93f8-ac9ecc8479c8`

```json
{
    "id": "e9066f04-8cc7-4616-93f8-ac9ecc8479c8",
    "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
    "createdDate": "2023-06-17T18:32:07.480+02:00",
    "updatedDate": "2023-06-17T18:32:07.551+02:00",
    "version": 1,
    "language": "de",
    "archived": false,
    "voucherStatus": "draft",
    "voucherNumber": "GS0007",
    "voucherDate": "2023-02-22T00:00:00.000+01:00",
    "address": {
        "name": "Bike & Ride GmbH & Co. KG",
        "supplement": "Gebäude 10",
        "street": "Musterstraße 42",
        "city": "Freiburg",
        "zip": "79112",
        "countryCode": "DE"
    },
    "lineItems": [
        {
            "type": "custom",
            "name": "Abus Kabelschloss Primo 590 ",
            "description": "- 9,5 mm starkes, smoke-mattes Spiralkabel mit integrierter Halterlösung zur Befestigung am Sattelklemmbolzen\n- bewährter Qualitäts-Schließzylinder mit praktischem Wendeschlüssel\n- KabelØ: 9,5 mm, Länge: 150 cm",
            "quantity": 2,
            "unitName": "Stück",
            "unitPrice": {
                "currency": "EUR",
                "netAmount": 13.4,
                "grossAmount": 15.946,
                "taxRatePercentage": 19
            },
            "lineItemAmount": 26.8
        },
        {
            "type": "custom",
            "name": "Energieriegel Testpaket",
            "quantity": 1,
            "unitName": "Stück",
            "unitPrice": {
                "currency": "EUR",
                "netAmount": 5,
                "grossAmount": 5,
                "taxRatePercentage": 0
            },
            "lineItemAmount": 5
        }
    ],
    "totalPrice": {
        "currency": "EUR",
        "totalNetAmount": 31.8,
        "totalGrossAmount": 36.89,
        "totalTaxAmount": 5.09
    },
    "taxAmounts": [
        {
            "taxRatePercentage": 0,
            "taxAmount": 0,
            "netAmount": 5
        },
        {
            "taxRatePercentage": 19,
            "taxAmount": 5.09,
            "netAmount": 26.8
        }
    ],
    "taxConditions": {
        "taxType": "net"
    },
    "title": "Rechnungskorrektur",
    "introduction": "Rechnungskorrektur zur Rechnung RE-00020",
    "remark": "Folgende Lieferungen/Leistungen schreiben wir Ihnen gut."
}
```

Note: This draft credit note has **no `paymentConditions`, no `shippingConditions`, no
`expirationDate`, no `dueDate`**. The related-invoice link, if any, is **NOT in the printed document**
— the docs say to put the invoice number in `introduction` (here `"Rechnungskorrektur zur Rechnung
RE-00020"`). Its `relatedVouchers` would carry the invoice ref once pursued. `title` defaults to
`"Rechnungskorrektur"`. Status enum: `draft | open | paidoff | voided`. Note `grossAmount: 15.946`
(3 decimals on the unit price here — see gotcha on rounding).

### Delivery Note — `GET /v1/delivery-notes/e9066f04-8cc7-4616-93f8-ac9ecc8479c8`

```json
{
    "id": "e9066f04-8cc7-4616-93f8-ac9ecc8479c8",
    "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
    "createdDate": "2023-06-17T18:32:07.480+02:00",
    "updatedDate": "2023-06-17T18:32:07.551+02:00",
    "version": 1,
    "language": "de",
    "archived": false,
    "voucherStatus": "draft",
    "voucherNumber": "LS0007",
    "voucherDate": "2023-02-22T00:00:00.000+01:00",
    "address": {
        "name": "Bike & Ride GmbH & Co. KG",
        "supplement": "Gebäude 10",
        "street": "Musterstraße 42",
        "city": "Freiburg",
        "zip": "79112",
        "countryCode": "DE"
    },
    "lineItems": [
        {
            "type": "custom",
            "name": "Abus Kabelschloss Primo 590 ",
            "description": "- 9,5 mm starkes, smoke-mattes Spiralkabel mit integrierter Halterlösung zur Befestigung am Sattelklemmbolzen\n- bewährter Qualitäts-Schließzylinder mit praktischem Wendeschlüssel\n- KabelØ: 9,5 mm, Länge: 150 cm",
            "quantity": 2,
            "unitName": "Stück",
            "unitPrice": {
                "currency": "EUR",
                "netAmount": 13.4,
                "grossAmount": 15.946,
                "taxRatePercentage": 19
            }
        },
        {
            "type": "custom",
            "name": "Energieriegel Testpaket",
            "quantity": 1,
            "unitName": "Stück",
            "unitPrice": {
                "currency": "EUR",
                "netAmount": 5,
                "grossAmount": 5,
                "taxRatePercentage": 0
            }
        }
    ],
    "taxConditions": {
        "taxType": "net"
    },
    "title": "Lieferschein",
    "introduction": "Lieferschein zur Rechnung RE-00020",
    "deliveryTerms": "Lieferung frei Haus.",
    "remark": "Folgende Lieferungen/Leistungen schreiben wir Ihnen gut."
}
```

Note: The delivery note is the **most stripped-down** type. **No `totalPrice`, no `taxAmounts`, no
`paymentConditions`, no `shippingConditions`, no `lineItemAmount` on line items** (unitPrice is present
in the read model but the docs say delivery notes "contain neither payment conditions nor prices,
reductions and tax amounts"). On **create**, the example sends `"unitPrice": null` for every line item.
Has `deliveryTerms`. `electronicDocumentProfile` is always `NONE`. Status enum: `draft | open` only.

### Dunning — `GET /v1/dunnings/a54820ca-ea27-11eb-8703-dffc93413c04`

```json
{
    "id": "e7f66576-d5c8-4dbd-9a01-c2c4d6695da6",
    "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
    "createdDate": "2023-07-21T15:26:51.469+02:00",
    "updatedDate": "2023-07-21T15:26:51.548+02:00",
    "version": 2,
    "language": "de",
    "archived": false,
    "voucherStatus": "draft",
    "voucherDate": "2023-07-22T01:00:00.000+02:00",
    "address": {
        "name": "Bike & Ride GmbH & Co. KG",
        "supplement": "Gebäude 10",
        "street": "Musterstraße 42",
        "city": "Freiburg",
        "zip": "79112",
        "countryCode": "DE"
    },
    "lineItems": [
        {
            "type": "custom",
            "name": "Energieriegel Testpaket",
            "quantity": 1,
            "unitName": "Stück",
            "unitPrice": {
                "currency": "EUR",
                "netAmount": 5,
                "grossAmount": 5.0,
                "taxRatePercentage": 0.0
            },
            "discountPercentage": 0,
            "lineItemAmount": 5.0
        },
        {
            "type": "text",
            "name": "Strukturieren Sie Ihre Belege durch Text-Elemente.",
            "description": "Das hilft beim Verständnis"
        }
    ],
    "totalPrice": {
        "currency": "EUR",
        "totalNetAmount": 5.0,
        "totalGrossAmount": 5.0,
        "totalTaxAmount": 0.0
    },
    "taxAmounts": [
        {
            "taxRatePercentage": 0.0,
            "taxAmount": 0.0,
            "netAmount": 5.0
        }
    ],
    "taxConditions": {
        "taxType": "net"
    },
    "shippingConditions": {
        "shippingDate": "2023-05-22T00:00:00.000+02:00",
        "shippingType": "delivery"
    },
    "relatedVouchers": [
        {
            "id": "ddc4c966-aae0-4e0e-a229-3ec9085ee9a3",
            "voucherNumber": "RE0357",
            "voucherType": "invoice"
        }
    ],
    "introduction": "Wir bitten Sie, die nachfolgend aufgelisteten Lieferungen/Leistungen unverzüglich zu begleichen.",
    "remark": "Sollten Sie den offenen Betrag bereits beglichen haben, betrachten Sie dieses Schreiben als gegenstandslos.",
    "title": "Mahnung"
}
```

Note: The dunning is the only type here that **shows a populated `relatedVouchers`** in the sample —
it always references its originating `invoice` (id + voucherNumber + voucherType). **No `voucherNumber`
of its own** in the read model (dunnings are not numbered like other vouchers), **no `expirationDate`,
no `dueDate`, no `paymentConditions`**. Status enum: `draft` only (always draft, never finalized).
`ä` appears literally in the docs' code sample text. Create MUST pass
`?precedingSalesVoucherId={invoiceId}`; contact ids and `taxConditions` must match the referenced
invoice, and the invoice's `address.name` is copied over (any `name` you send is ignored).

### Down Payment Invoice — `GET /v1/down-payment-invoices/28af0062-5b19-11eb-9609-57d780e21aed`

```json
{
  "id": "0333f0c7-2b89-4889-b64e-68b3ca3f167a",
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "createdDate": "2023-01-20T10:26:40.956+01:00",
  "updatedDate": "2023-01-21T13:34:13.228+01:00",
  "version": 3,
  "language": "de",
  "archived": false,
  "voucherStatus": "open",
  "voucherNumber": "RE1129",
  "voucherDate": "2023-01-20T10:26:26.565+01:00",
  "dueDate": "2023-02-19T00:00:00.000+01:00",
  "address": {
    "name": "Bike & Ride GmbH & Co. KG",
    "supplement": "Gebäude 10",
    "street": "Musterstraße 42",
    "city": "Freiburg",
    "zip": "79112",
    "countryCode": "DE"
  },
  "lineItems": [
    {
      "type": "custom",
      "name": "Pauschaler Abschlag",
      "quantity": 1,
      "unitPrice": {
        "currency": "EUR",
        "netAmount": 559.66,
        "grossAmount": 666,
        "taxRatePercentage": 19
      },
      "lineItemAmount": 666.00
    }
  ],
  "totalPrice": {
    "currency": "EUR",
    "totalNetAmount": 559.66,
    "totalGrossAmount": 666.00,
    "totalTaxAmount": 106.34
  },
  "taxAmounts": [
    {
      "taxRatePercentage": 19,
      "taxAmount": 106.34,
      "netAmount": 559.66
    }
  ],
  "taxConditions": {
    "taxType": "gross"
  },
  "paymentConditions": {
    "paymentTermLabel": "10 Tage - 3 %, 30 Tage netto",
    "paymentTermLabelTemplate": "{discountRange} Tage -{discount}, {paymentRange} Tage netto",
    "paymentTermDuration": 30,
    "paymentDiscountConditions": {
      "discountPercentage": 3,
      "discountRange": 10
    }
  },
  "shippingConditions": {
    "shippingType": "none"
  },
  "closingInvoiceId": "4ba90e2d-c206-4bb0-a135-3e714db617fb",
  "introduction": "Wie vereinbart, erlauben wir uns folgenden pauschalen Abschlag in Rechnung zu stellen.",
  "remark": "Vielen Dank für die gute Zusammenarbeit.",
  "files": {
    "documentFileId": "aa0388c5-20b5-49d7-96ce-0c08ac0482f4"
  },
  "title": "1. Abschlagsrechnung"
}
```

Note: This is closest to a real invoice — it has `dueDate`, `paymentConditions`, `shippingConditions`
and a **`closingInvoiceId`** ("Id of the closing invoice that references this down payment invoice, if
one exists. Null otherwise."). In the "Properties" sample `closingInvoiceId` is `null` and
`relatedVouchers` is `[]`; in this retrieved sample it is populated. Status enum:
`draft | open | paid | voided`. Read-only — you cannot create or edit down-payment invoices via API.

### Shared: create response envelope (POST 201) — same shape for all writable types

```json
{
  "id": "a6d29b44-e5c1-43f2-9403-6859aba4104a",
  "resourceUri": "https://api.lexware.io/v1/quotations/a6d29b44-e5c1-43f2-9403-6859aba4104a",
  "createdDate": "2023-03-18T12:37:25.616+01:00",
  "updatedDate": "2023-03-18T12:37:25.616+01:00",
  "version": 1
}
```

Note: POST returns only this stub (id/resourceUri/version), **not** the full resource — you must GET
by id to read the computed prices/status. `resourceUri` swaps the path segment per type
(`/v1/credit-notes/...`, `/v1/dunnings/...`, etc.).

### Shared: render-document response — `GET /v1/{type}/{id}/document`

```json
{
  "documentFileId": "b26e1d73-19ff-46b1-8929-09d8d73d4167"
}
```

Note: identical shape for every type. Then download binary via `GET /v1/{type}/{id}/file` (or the
Files endpoint) with `Accept: */*`.

### Shared: vat-free (reverse-charge) taxConditions snippet

```json
"taxConditions": {
    "taxType": "constructionService13b",
    "taxTypeNote": "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)"
}
```

Note: appears verbatim in every type's Properties section. `taxTypeNote` is only present for the
§13b / vat-free types.

---

## Key fields

| Field | Type | Meaning |
|-------|------|---------|
| `id` | uuid | Resource id, generated by Lexware. Read-only. |
| `organizationId` | uuid | Owning organization. Read-only. |
| `version` | integer | Optimistic-locking revision. **Starts at 0** for a fresh draft (see order-confirmation sample), increments on every change. Read-only. Note: none of these six endpoints expose an update (`PUT`) operation, so there is no write path that consumes `version` here — it is carried for platform consistency (drafts are edited in the Lexware UI, not via API). |
| `voucherStatus` | enum | Status — **enum set differs per type** (see Gotchas). Read-only. |
| `voucherNumber` | string | Human number assigned by Lexware on finalization (`AG…` quotation, `AB…` order-conf, `GS…` credit note, `LS…` delivery note, `RE…` (down-payment) invoice). **Dunnings have none.** Read-only. |
| `voucherDate` | dateTime | Document date. RFC 3339 / ISO 8601, ms + offset, e.g. `2023-02-22T00:00:00.000+01:00`. |
| `expirationDate` | dateTime | **Quotations only** — when the quote expires. |
| `dueDate` | dateTime | **Down-payment invoices (and invoices) only** — payable-by date before overdue. |
| `electronicDocumentProfile` | enum | `NONE` \| `EN16931` (ZUGFeRD) \| `XRechnung`. For every non-invoice sales doc it is **always `NONE`**; only (finalized) invoices and down-payment invoices can be `EN16931`/`XRechnung`. Read-only. |
| `address` | object | Recipient. `contactId` (uuid, nullable) links a Lexware contact; if absent the doc targets the "collective customer". `name, supplement, street, city, zip, countryCode`. |
| `lineItems[].type` | enum | `service` \| `material` (both reference a Lexware product/service by `id`) \| `custom` (no reference, no id) \| `text` (name/description only, informational). Max **300** line items. |
| `lineItems[].id` | uuid | Reference to an existing product/service (present for `material`/`service`), else absent/null. |
| `lineItems[].quantity` | number | Up to 4 decimals. |
| `lineItems[].discountPercentage` | number | Up to 2 decimals. |
| `lineItems[].lineItemAmount` | number | Line total, net or gross per `taxType`. Up to 2 decimals. Read-only. **Absent on delivery notes.** |
| `lineItems[].optional` | boolean | **Quotations only.** "Optionale Position". Not valid on subitems. Default false. |
| `lineItems[].alternative` | boolean | **Quotations only.** Alternative position. Valid **only on subitems**, where it is **mandatory `true`**. Default false. |
| `lineItems[].subItems` | list | **Quotations only.** Nested line items; currently all subItems must be `alternative`. |
| `unitPrice` | object | `currency` (only `EUR`), `netAmount`, `grossAmount`, `taxRatePercentage`. On create you send net OR gross depending on `taxType`; the other is computed. |
| `totalPrice` | object | `currency, totalNetAmount, totalGrossAmount, totalTaxAmount` (all read-only, up to 2 dp) + optional writable `totalDiscountAbsolute`, `totalDiscountPercentage`. **Absent on delivery notes.** |
| `taxAmounts[]` | list | Per-rate breakdown `{taxRatePercentage, taxAmount, netAmount}`. Read-only (submitted values ignored). **Absent on delivery notes.** |
| `taxConditions.taxType` | enum | `net` \| `gross` \| `vatfree` \| `intraCommunitySupply` \| `constructionService13b` \| `externalService13b` \| `thirdPartyCountryService` \| `thirdPartyCountryDelivery` \| `photovoltaicEquipment`. |
| `taxConditions.taxTypeNote` | string | Free note; auto-set for §13b/reverse-charge types. |
| `paymentConditions` | object | `paymentTermLabel`, `paymentTermLabelTemplate` (`{discountRange}`/`{discount}`/`{paymentRange}` placeholders), `paymentTermDuration` (days), `paymentDiscountConditions{discountPercentage,discountRange}`. **Absent on delivery notes & dunnings.** |
| `shippingConditions` | object | `shippingDate`, `shippingEndDate`, `shippingType` = `service` \| `serviceperiod` \| `delivery` \| `deliveryperiod` \| `none`. Present on order-confirmations, dunnings, down-payment invoices. |
| `relatedVouchers[]` | list | `{id, voucherNumber, voucherType}` of linked vouchers. Read-only. Populated e.g. on a dunning (→ its invoice) or a pursued credit note. |
| `closingInvoiceId` | uuid | **Down-payment invoices only.** Id of the closing (final) invoice that settles this down payment; null if none. |
| `deliveryTerms` | string | Free text; on delivery notes and order confirmations. |
| `title` / `introduction` / `remark` | string | Header title, intro/header text, closing text. Localized defaults applied per `language` if omitted. |
| `printLayoutId` | uuid | Optional print layout; org default if omitted. |
| `files.documentFileId` | uuid | Id of the generated PDF. **Deprecated** ("will be removed") — prefer the `/document` + Files-endpoint flow. |
| `language` | string | ISO 639-1, `de` (default) or `en`. |
| `archived` | boolean | Archived-in-Lexware flag. Read-only. |

---

## Gotchas

- **`voucherStatus` enum is different for every type** — a CLI must not use one status list:
  - quotation: `draft | open | accepted | rejected`
  - order-confirmation: `draft | open`
  - delivery-note: `draft | open`
  - credit-note: `draft | open | paidoff | voided`
  - dunning: `draft` (only — always draft, never finalized)
  - down-payment-invoice: `draft | open | paid | voided`
  (Regular invoice, for comparison: `draft | open | paid | voided`; the Voucherlist adds a derived
  `overdue` bucket = open/sepadebit past dueDate — the per-resource endpoints never return `overdue`.)
- **draft vs finalized**: POST creates a `draft` unless `?finalize=true` (quotations,
  order-confirmations, credit-notes, delivery-notes). A draft is editable; once `open` it is immutable
  and the PDF (`files.documentFileId`) is generated. **Dunnings ignore `finalize` — always draft.**
  **Down-payment invoices can't be created at all** (read-only endpoint).
- **The PDF is a two-step, and `files.documentFileId` is deprecated.** Call `GET /{type}/{id}/document`
  → `{documentFileId}`, then download via the Files endpoint (`GET /v1/files/{documentFileId}` or
  `GET /{type}/{id}/file`) with `Accept: */*`. Don't rely on the `files` object in the resource.
- **Money is stored as both net and gross on every price object**; which one is authoritative depends
  on `taxConditions.taxType` (`net` vs `gross`). Read-only totals (`totalPrice`, `taxAmounts`,
  `lineItemAmount`) are computed server-side and ignored on write. To create, send only net OR gross on
  `unitPrice` matching the taxType.
- **Rounding oddity**: unit `grossAmount` can carry **more than 2 decimals** (e.g. credit-note
  `15.946`), while totals are 2 dp. Don't assume 2-dp on unitPrice.
- **Delivery notes have no prices/tax/totals** in practice: no `totalPrice`, no `taxAmounts`, no
  `lineItemAmount`; create examples send `unitPrice: null`. Any "value of goods" a user wants must be
  computed elsewhere.
- **Pursue vs create share the same POST path**; the only difference is the
  `?precedingSalesVoucherId={id}` query param, which builds the document chain and populates
  `relatedVouchers`. Invalid pursue → **HTTP 406** (not 400). Specific 406 triggers: pursuing a `draft`
  invoice to a credit note; pursuing a quotation that has `alternative`/`optional` line items into an
  order-confirmation or delivery-note; pursuing a `draft` order-confirmation into a delivery-note; a
  closing invoice cannot be pursued to a credit note.
- **The related/preceding document is NOT printed.** Credit notes and delivery notes do not show the
  source invoice number on the PDF — the docs' own workaround is to embed it in `introduction`. So the
  linkage lives only in `relatedVouchers` (via the API), not on the customer-facing document.
- **Dunning specifics**: `precedingSalesVoucherId` is **mandatory**; contact ids of dunning and invoice
  must match (or both absent → collective customer); `taxConditions` must equal the invoice's; the
  `address.name` you send is ignored (copied from the invoice). Dunnings have no `voucherNumber`.
- **Quotation scope is not auto-granted.** API keys created before the quotations endpoint shipped lack
  quotation permission — the key must be regenerated. A CLI hitting 403 on `/v1/quotations` should tell
  the user to regenerate their key.
- **Date format** is RFC 3339 / ISO 8601 with milliseconds and offset: `2023-02-22T00:00:00.000+01:00`.
  Offsets swing between `+01:00` and `+02:00` across samples (Europe/Berlin DST) — treat as instants,
  not local dates. `id` (uuid) ≠ `voucherNumber` (human string); filter/link by the right one.
- **`electronicDocumentProfile` is always `NONE`** for quotations/order-confirmations/delivery-notes/
  dunnings — ZUGFeRD/XRechnung only exist for invoices and down-payment invoices.
- **No list endpoints.** None of these six can be listed directly; use the Voucherlist endpoint to find
  ids (filter by `voucherType`, `voucherStatus`) then GET each. Expect Voucherlist to be the paginated
  Spring "Pageable" wrapper; the per-resource GETs return a bare object, not a page. **Dunnings are the
  exception even here — they do not appear in Voucherlist at all** (`voucherType` has no `dunning`
  value); find them only via an invoice's `relatedVouchers` or a known dunning id.
- **No update endpoint (no `PUT`).** These endpoints are create + read only (plus render/download). You
  cannot edit a draft or change status via the API — editing/finalizing beyond the initial
  `?finalize=true` happens in the Lexware UI. So a CLI's "edit" verb has nothing to call; the `version`
  field never guards a write here.
- **Down-payment invoices are numbered `RE…` like invoices** and use `taxType: gross` in the sample —
  don't mistake them for regular invoices; they live on their own read-only endpoint and carry
  `closingInvoiceId`.

---

## What the API refuses to answer directly (compute-it-yourself → killer-feature fuel)

Everything here is single-resource CRUD with no aggregation, no list endpoint, and no cross-document
rollups. A user will want, and the API will not give:

- **"What is the total open receivables / value of unpaid down-payment invoices?"** No sum endpoint;
  you must page Voucherlist, GET each `open` down-payment invoice, and sum `totalPrice.totalGrossAmount`
  yourself (per-status, per-currency).
- **"Which invoices are overdue and by how much?"** The per-resource endpoints never return `overdue`
  (only Voucherlist derives it). Overdue buckets (0–30/31–60/60+ days) must be computed from `dueDate`
  vs today — and only down-payment invoices/invoices even have `dueDate`.
- **"Show me the full document chain for this deal (quote → order-confirmation → delivery-note →
  invoice → dunning/credit-note)."** `relatedVouchers` only lists immediate neighbors and is often empty
  or one-hop; there is no chain/graph endpoint. The tool must walk `relatedVouchers` +
  `precedingSalesVoucherId` links transitively and reconstruct the chain.
- **"Convert this quotation into an order confirmation / invoice"** — there is no conversion call; you
  must POST to the target endpoint with `?precedingSalesVoucherId`, pre-filtering out
  `alternative`/`optional` line items yourself or the API 406s. Quote acceptance rate
  (accepted vs rejected vs expired) must be tallied client-side from `voucherStatus` + `expirationDate`.
- **"How much did we credit back last quarter?" / "outstanding down payments not yet closed"** — no
  period revenue, credit-note totals, or "down payments without a `closingInvoiceId`" query; iterate and
  aggregate. `closingInvoiceId == null` is the only signal that a down payment is still open, and it's
  per-record.
- **"Which quotations are expiring in the next 7 days?"** No filter on `expirationDate`; fetch and
  filter client-side.
- **"Net vs gross revenue for a tax rate / reverse-charge exposure."** `taxAmounts` is per document
  only; cross-document tax summaries must be assembled by the tool.
- **Duplicate detection, per-customer receivable rollups, dunning candidates (open invoices past
  dueDate with no dunning yet)** — none exist server-side; all are derivations the CLI can own.

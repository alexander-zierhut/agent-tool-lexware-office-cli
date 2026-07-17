# Bookkeeping — Lexware Office API

Source: https://developers.lexware.io/docs/ (single static Slate HTML page, fetched 2026-07-18).
All JSON below is quoted **verbatim** from the official docs (real UUIDs, dates, enum values).
Base URL `https://api.lexware.io` (legacy `https://api.lexware.com` until Dec 2025). Auth header
`Authorization: Bearer <apiKey>`. `Accept: application/json`. Rate limit 2 req/s → HTTP 429.

This area covers five endpoints:
**vouchers**, **voucherlist**, **payments**, **payment-conditions**, **posting-categories** —
plus the cross-referenced paging and tax-rate rules that affect them.

---

## Endpoints

| METHOD | /v1/path | Purpose | Notes / permissions |
|--------|----------|---------|---------------------|
| POST | `/v1/vouchers` | Create a bookkeeping voucher | Body = voucher JSON without read-only fields. `version` if present must be `1`. Created voucher appears at app.lexware.de/vouchers. |
| GET | `/v1/vouchers/{id}` | Retrieve one voucher by id | Returns full voucher incl. `voucherItems`, `files`, `version`. |
| PUT | `/v1/vouchers/{id}` | Update / merge a voucher | Requires current `version` or **HTTP 409 Conflict**. Cannot change `voucherStatus` except finalizing `unchecked`→`open`. An `unchecked` voucher otherwise may not be updated. |
| GET | `/v1/vouchers?voucherNumber={n}` | Filter vouchers by voucher number | **DEPRECATED** — docs say use voucherlist instead. Returns a Pageable page. |
| POST | `/v1/vouchers/{id}/files` | Upload/assign a file (pdf/image/xml) to a voucher | `multipart/form-data`, field `file`. Dedup by checksum → may return an existing file id. Omitting file ids on a voucher PUT **permanently deletes** them. |
| GET | `/v1/voucherlist?voucherType=..&voucherStatus=..` | List/filter voucher **metadata** across all document types | **This is the open/paid/overdue query.** `voucherType` and `voucherStatus` are BOTH mandatory. Covers bookkeeping vouchers AND invoices, credit notes, quotations, order confirmations, delivery notes, down-payment invoices. |
| GET | `/v1/payments/{voucherId}` | Retrieve payment status/items of a voucher | Read-only. Errors for voucher types without payment info (quotations, drafts, invoice-linked credit notes). |
| GET | `/v1/payment-conditions` | List configured payment conditions | Returns a **bare JSON array** (NOT a Pageable page). |
| GET | `/v1/posting-categories` | List all booking categories (`income`/`outgo`) | Returns a **bare JSON array**. Authoritative source of `categoryId`s. |

Deeplinks (browser, not API): `{appbaseurl}/permalink/vouchers/view/{voucherId}` and `.../edit/{voucherId}`.

---

## Response examples

### 1. Voucher object — multi-item, different tax rates, collective contact (GET /v1/vouchers/{id})

```json
{
    "id": "a8691b5d-2393-4317-888d-bcd5d564f7d1",
    "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
    "type": "salesinvoice",
    "voucherStatus": "open",
    "voucherNumber": "2023-000321",
    "voucherDate": "2023-06-30T00:00:00.000+02:00",
    "shippingDate": "2023-07-02T00:00:00.000+02:00",
    "dueDate": "2023-07-07T00:00:00.000+02:00",
    "totalGrossAmount": 326.00,
    "totalTaxAmount": 26.00,
    "taxType": "gross",
    "useCollectiveContact": true,
    "remark": "Bestellung von Max Mustermann.",
    "voucherItems": [
        {
            "amount": 119.00,
            "taxAmount": 19.00,
            "taxRatePercent": 19.00,
            "categoryId": "8f8664a8-fd86-11e1-a21f-0800200c9a66"
        },
        {
            "amount": 107.00,
            "taxAmount": 7.00,
            "taxRatePercent": 7.00,
            "categoryId": "8f8664a8-fd86-11e1-a21f-0800200c9a66"
        },
        {
            "amount": 100.00,
            "taxAmount": 0,
            "taxRatePercent": 0.00,
            "categoryId": "8f8664a8-fd86-11e1-a21f-0800200c9a66"
        }
    ],
    "files": [],
    "createdDate": "2023-06-30T13:28:51.012+02:00",
    "updatedDate": "2023-06-30T13:28:51.012+02:00",
    "version": 2
}
```
Note: `voucherDate`/`shippingDate`/`dueDate` are returned as full RFC-3339 datetimes with TZ
offset, even though they are **sent** as plain `yyyy-MM-dd`. `taxAmount: 0` and `taxRatePercent: 0.00`
show the docs are inconsistent about `##.00` formatting (numbers, not strings).

### 2. Create a Voucher — request body (POST /v1/vouchers)

```json
{
  "type": "salesinvoice",
  "voucherNumber": "123-456",
  "voucherDate": "2023-06-28",
  "shippingDate": "2023-07-02",
  "dueDate": "2023-07-05",
  "totalGrossAmount": 119.00,
  "totalTaxAmount": 19.00,
  "taxType": "gross",
  "useCollectiveContact": true,
  "remark": "Bestellung von Max Mustermann.",
  "voucherItems": [{
    "amount": 119.00,
    "taxAmount": 19.00,
    "taxRatePercent": 19,
    "categoryId": "8f8664a8-fd86-11e1-a21f-0800200c9a66"
    }]
}
```
Note: dates sent as bare `yyyy-MM-dd`. No `version`/`id`/`organizationId`/`createdDate` in the request.

### 3. Create a Voucher — response (POST /v1/vouchers → 201)

```json
{
  "id": "66196c43-baf3-4335-bfee-d610367059db",
  "resourceUri": "https://api.lexware.io/v1/vouchers/66196c43-baf3-4335-bfee-d610367059db",
  "createdDate": "2023-06-29T15:15:09.447+02:00",
  "updatedDate": "2023-06-29T15:15:09.447+02:00",
  "version": 1
}
```
Note: creation returns only the id/resourceUri/timestamps/version stub — NOT the full voucher.
`version` starts at `1` after creation. Fetch the full object with GET.

### 4. Retrieve a Voucher — response (GET /v1/vouchers/{id})

```json
{
  "id": "66196c43-baf3-4335-bfee-d610367059db",
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "type": "salesinvoice",
  "voucherStatus": "open",
  "voucherNumber": "123-456",
  "voucherDate": "2023-06-28T00:00:00.000+02:00",
  "shippingDate": "2023-07-02T00:00:00.000+02:00",
  "dueDate": "2023-07-05T00:00:00.000+02:00",
  "totalGrossAmount": 119,
  "totalTaxAmount": 19.00,
  "taxType": "gross",
  "useCollectiveContact": true,
  "remark": "Bestellung von Max Mustermann.",
  "voucherItems": [
    {
      "amount": 119,
      "taxAmount": 19.00,
      "taxRatePercent": 19,
      "categoryId": "8f8664a8-fd86-11e1-a21f-0800200c9a66"
    }
  ],
  "files": [],
  "createdDate": "2023-06-29T15:15:09.447+02:00",
  "updatedDate": "2023-06-29T15:15:09.447+02:00",
  "version": 1
}
```

### 5. Filter vouchers by number — Pageable response (GET /v1/vouchers?voucherNumber=123-456-789) — DEPRECATED

```json
{
  "content": [
    {
      "id": "dba9418a-2381-48cd-afa3-81c0c1d0e53e",
      "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
      "type": "purchaseinvoice",
      "voucherNumber": "123-456-789",
      "voucherDate": "2023-01-31T00:00:00.000+01:00",
      "dueDate": "2023-01-31T00:00:00.000+01:00",
      "totalGrossAmount": 1000,
      "totalTaxAmount": 159.66,
      "taxType": "gross",
      "useCollectiveContact": true,
      "remark": "Test",
      "voucherItems": [
        {
          "amount": 1000,
          "taxAmount": 159.66,
          "taxRatePercent": 19,
          "categoryId": "16d04a28-fd91-11e1-a21f-0800200c9a66"
        }
      ],
      "files": [],
      "createdDate": "2023-01-16T07:58:21.849+01:00",
      "updatedDate": "2023-01-16T07:58:21.849+01:00",
      "version": 0
    },
    {
      "id": "0a739052-ce80-4ae6-a276-34524eec43b1",
      "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
      "type": "salesinvoice",
      "voucherNumber": "123-456-789",
      "voucherDate": "2023-01-31T00:00:00.000+01:00",
      "dueDate": "2023-01-31T00:00:00.000+01:00",
      "totalGrossAmount": 500,
      "totalTaxAmount": 79.83,
      "taxType": "gross",
      "useCollectiveContact": true,
      "remark": "Test-2",
      "voucherItems": [
        {
          "amount": 500,
          "taxAmount": 79.83,
          "taxRatePercent": 19,
          "categoryId": "4f01e761-d912-441f-ad1a-1c1d2d590a81"
        }
      ],
      "files": [],
      "createdDate": "2023-01-16T07:59:32.277+01:00",
      "updatedDate": "2023-01-16T07:59:32.277+01:00",
      "version": 0
    }
  ],
  "totalPages": 1,
  "totalElements": 2,
  "last": true,
  "numberOfElements": 2,
  "first": true,
  "size": 25,
  "number": 0
}
```
Note: this bare-`/v1/vouchers` filter page has **no `sort` array** (unlike voucherlist). `version: 0`
here (older docs example) vs `1` in the newer create example — versions are just monotonic counters.

### 6. Voucherlist — Pageable response (GET /v1/voucherlist?voucherType=purchaseinvoice,invoice&voucherStatus=open&voucherDateFrom=2023-03-01)

**This is the killer-feature source: open / paid / overdue documents across all types.**

```json
{
    "content": [
        {
            "id": "57b8d457-1fb6-4ae9-944a-9fe763da2aff",
            "voucherType": "purchaseinvoice",
            "voucherStatus": "open",
            "voucherNumber": "2010096",
            "voucherDate": "2023-06-14T00:00:00.000+02:00",
            "createdDate": "2023-03-22T12:36:22.000+01:00",
            "updatedDate": "2023-03-22T12:36:22.000+01:00",
            "dueDate": "2023-06-21T00:00:00.000+02:00",
            "contactId": null,
            "contactName": "Sammellieferant",
            "totalAmount": 80.04,
            "openAmount": 80.04,
            "currency": "EUR",
            "archived": false
        },
        {
            "id": "f3d3ae48-30d9-4b56-973a-b3159cbe743c",
            "voucherType": "invoice",
            "voucherStatus": "open",
            "voucherNumber": "RE1012",
            "voucherDate": "2023-05-14T00:00:00.000+02:00",
            "createdDate": "2023-05-14T16:52:21.000+02:00",
            "updatedDate": "2023-05-14T16:52:21.000+02:00",
            "dueDate": "2023-05-24T00:00:00.000+02:00",
            "contactId": "777c7793-9fbb-4ec7-9254-0619c199761e",
            "contactName": "Musterfrau, Erika",
            "totalAmount": 99.8,
            "openAmount": 74.8,
            "currency": "EUR",
            "archived": false
        },
        {
            "id": "55aa6de8-d32d-47bd-9c3c-d541ab65a8e8",
            "voucherType": "invoice",
            "voucherStatus": "overdue",
            "voucherNumber": "RE1011",
            "voucherDate": "2023-03-02T00:00:00.000+01:00",
            "createdDate": "2023-03-03T16:52:21.000+01:00",
            "updatedDate": "2023-03-03T16:52:21.000+01:00",
            "dueDate": "2023-10-06T00:00:00.000+02:00",
            "contactId": "b08a1ac7-10fc-4214-b875-8491f91479dd",
            "contactName": "Test GmbH",
            "totalAmount": 498.8,
            "openAmount": 498.8,
            "currency": "EUR",
            "archived": false
        }
    ],
    "first": true,
    "last": true,
    "totalPages": 1,
    "totalElements": 3,
    "numberOfElements": 3,
    "size": 25,
    "number": 0,
    "sort": [
        {
            "property": "voucherdate",
            "direction": "DESC",
            "ignoreCase": false,
            "nullHandling": "NATIVE",
            "ascending": false
        }
    ]
}
```
Note: default sort is `voucherdate DESC`. `totalAmount` here is the whole invoice; `openAmount` is
what's still unpaid (see row 2: total 99.8, open 74.8 = 25.00 already paid). `contactId` is `null`
for the collective contact ("Sammellieferant"). Amounts here are trimmed (`99.8`, not `99.80`).

### 7. Payments — four samples for different voucher types (shape of GET /v1/payments/{id})

```json
{
  "openAmount": 200.00,
  "currency": "EUR",
  "paymentStatus": "openRevenue",
  "voucherType": "invoice",
  "voucherStatus": "open",
  "paymentItems": []
}

{
  "openAmount": 39.90,
  "paymentStatus": "openExpense",
  "currency": "EUR",
  "voucherType": "purchaseinvoice",
  "voucherStatus": "open",
  "paymentItems": [
    {
      "paymentItemType": "manualPayment",
      "postingDate": "2023-11-07T00:00:00.000+01:00",
      "amount": 10.50,
      "currency": "EUR"
    },
    {
      "paymentItemType": "manualPayment",
      "postingDate": "2023-11-13T00:00:00.000+01:00",
      "amount": 20.0,
      "currency": "EUR"
    }
  ]
}

{
  "openAmount": 0.0,
  "currency": "EUR",
  "paymentStatus": "balanced",
  "voucherType": "purchasecreditnote",
  "voucherStatus": "paidoff",
  "paidDate": "2023-07-14T13:42:02.123+02:00",
  "paymentItems": [
    {
      "paymentItemType": "manualPayment",
      "postingDate": "2023-07-14T00:00:00.000+01:00",
      "amount": 119.0,
      "currency": "EUR"
    }
  ]
}

{
  "openAmount": 0.0,
  "paymentStatus": "balanced",
  "currency": "EUR",
  "voucherType": "invoice",
  "voucherStatus": "paid",
  "paidDate": "2023-07-14T13:42:02.123+02:00",
  "paymentItems": [
    {
      "paymentItemType": "manualPayment",
      "postingDate": "2023-07-14T00:00:00.000+01:00",
      "amount": 72.0,
      "currency": "EUR"
    },
    {
      "paymentItemType": "cashDiscount",
      "postingDate": "2023-07-14T00:00:00.000+01:00",
      "amount": 7.85,
      "currency": "EUR"
    }
  ]
}
```
Note: these are four separate example objects concatenated in the docs (each is one payment
response). `paidDate` is only present when `voucherStatus` is `paid` or `paidoff`. `openAmount` is
always a **positive** value for both revenue and expense — sign comes from `paymentStatus`.

### 8. Payments — retrieve response (GET /v1/payments/1f1dc13c-fd68-11ea-a8b9-ff40c7cabfe0)

```json
{
  "openAmount": "1337.00",
  "currency": "EUR",
  "paymentStatus": "openRevenue",
  "voucherType": "salesinvoice",
  "voucherStatus": "open",
  "paymentItems": [
    {
      "paymentItemType": "manualPayment",
      "postingDate": "2023-11-04T00:00:00.000+01:00",
      "amount": 10.0,
      "currency": "EUR"
    },
    {
      "paymentItemType": "manualPayment",
      "postingDate": "2023-11-06T00:00:00.000+01:00",
      "amount": 39.99,
      "currency": "EUR"
    }
  ]
}
```
Note: **`openAmount` is a quoted string `"1337.00"` here** but an unquoted number `200.00` / `0.0`
in the samples above — the CLI must tolerate money as *either* JSON number or JSON string.

### 9. Payment Conditions — list response (GET /v1/payment-conditions)

```json
[
    {
        "id": "65be0654-60b6-11eb-b66d-5731dbc9bf6b",
        "paymentTermLabelTemplate": "Zahlbar in {paymentRange} Tagen, rein netto ohne Abzug",
        "paymentTermDuration": 14,
        "organizationDefault": false
    },
    {
        "id": "3fcc62d1-0925-456d-890b-779b56e7289e",
        "paymentTermLabelTemplate": "10 Tage - 3 %, 30 Tage netto",
        "paymentTermDuration": 30,
        "paymentDiscountConditions": {
            "discountRange": 10,
            "discountPercentage": 3.00
        },
        "organizationDefault": true
    }
]
```
Note: bare array, not paged. `paymentTermLabelTemplate` may contain `{...}` placeholders (e.g.
`{paymentRange}`, `{discountRange}`) — it is a template, not a rendered string. `paymentDiscountConditions`
is absent when no discount ("Skonto") applies. Exactly one entry has `organizationDefault: true`.

### 10. Posting Categories — list response (GET /v1/posting-categories)

```json
[
  {
      "id": "cf03a2b0-f838-474f-ac5e-67adb9b830c7",
      "name": "Reise MA",
      "type": "outgo",
      "contactRequired": false,
      "splitAllowed": true,
      "groupName": "Reisen"
  },
  {
      "id": "3620798f-ae06-4492-b775-1c87eb99247c",
      "name": "Fahrtkosten MA",
      "type": "outgo",
      "contactRequired": false,
      "splitAllowed": true,
      "groupName": "Reisen"
  },
  {
      "id": "8f8664a1-fd86-11e1-a21f-0800200c9a66",
      "name": "Einnahmen",
      "type": "income",
      "contactRequired": false,
      "splitAllowed": true,
      "groupName": "Einnahmen"
  },
  {
      "id": "8f8664a0-fd86-11e1-a21f-0800200c9a66",
      "name": "Dienstleistung",
      "type": "income",
      "contactRequired": false,
      "splitAllowed": true,
      "groupName": "Einnahmen"
  }
]
```
Note: bare array. `type` is `income` (revenue → salesinvoice/salescreditnote) or `outgo` (expense →
purchaseinvoice/purchasecreditnote). This endpoint is the authoritative `categoryId` source.

### 11. Generic Pageable envelope (from "Paging of Resources")

```json
{
  "content":[
    ...
  ],
  "first": true,
  "last": true,
  "totalPages": 1,
  "totalElements": 13,
  "numberOfElements": 13,
  "size": 25,
  "number": 0,
  "sort": [
      {
        "direction": "ASC",
        "property": "name",
        "ignoreCase": false,
        "nullHandling": "NATIVE",
        "ascending": true
      }
  ]
}
```

---

## Key fields

### Voucher (vouchers endpoint)

| Field | Type | Meaning |
|-------|------|---------|
| `id` | uuid | Voucher id, generated by Lexware on create. |
| `organizationId` | uuid | Owning organization. Read-only. |
| `type` | enum | `salesinvoice`, `salescreditnote`, `purchaseinvoice`, `purchasecreditnote`. (This is the **bookkeeping voucher** `type` field — narrower than voucherlist's `voucherType`.) Same `categoryId` may serve salescreditnote and salesinvoice. |
| `voucherStatus` | enum | Billing state: `blank`, `open`, `paid`, `paidoff`, `voided`, `transferred`, `sepadebit`, `unchecked`. **Only `open` and `unchecked` are writeable.** `blank` vouchers are read-only, ignore until unchecked/open. |
| `voucherNumber` | string | Reference/order number. Mandatory unless status `unchecked`. |
| `voucherDate` | date (in) / dateTime (out) | Issue date. **Sent** as `yyyy-MM-dd`; **returned** as RFC-3339 datetime. |
| `shippingDate` | date | Delivery/service date (period → end date). **Only for `salesinvoice`/`salescreditnote`.** |
| `dueDate` | date | Payment due date. Defaults to `voucherDate` if omitted (unless `unchecked` → stays unset). |
| `totalGrossAmount` | number | Total gross; must equal sum of positions + tax. Format `##.00`. |
| `totalTaxAmount` | number | Total tax; must equal sum of positions' tax. Format `##.00`. |
| `taxType` | enum | `net` (item amounts are net, add tax) or `gross` (tax included). |
| `useCollectiveContact` | boolean | `true` → use Lexware's collective contact; `contactId` then ignored. |
| `contactName` | string | Recipient/invoicing party name. Overriding it makes an individual name but keeps the collective-contact link (does not rename the collective contact). |
| `contactId` | uuid | Existing contact (must pre-exist via Contacts endpoint). Its role must be Customer, or Customer+Vendor. |
| `remark` | string | Free text; part of Lexware full-text search. |
| `voucherItems` | list | Positions grouped by tax rate — see below. |
| `files` | list<uuid> | Attached voucher-image file ids. **Omitting an existing id on PUT deletes that file permanently.** |
| `createdDate` / `updatedDate` | dateTime | RFC-3339. Read-only. |
| `version` | integer | Optimistic-lock counter. POST with `0` (or omit; if present must be 1 per create table); PUT must send latest version from a fresh GET. |

**voucherItems** object: `amount` (number, net or gross per `taxType`), `taxAmount` (number),
`taxRatePercent` (number, e.g. `19`), `categoryId` (uuid, booking category). All four required.

### Voucherlist metadata (voucherlist endpoint — a DIFFERENT, wider shape)

| Field | Type | Meaning |
|-------|------|---------|
| `id` | uuid | Voucher id (fetch full object via the type-specific endpoint). |
| `voucherType` | enum | `salesinvoice`, `salescreditnote`, `purchaseinvoice`, `purchasecreditnote`, `invoice`, `downpaymentinvoice`, `creditnote`, `orderconfirmation`, `quotation`, `deliverynote`. |
| `voucherStatus` | enum | `draft`, `open`, `paid`, `paidoff`, `voided`, `transferred`, `sepadebit`, `overdue`, `accepted`, `rejected`, `unchecked`. |
| `voucherNumber` | string | Reference number. |
| `voucherDate` / `createdDate` / `updatedDate` / `dueDate` | dateTime | RFC-3339. |
| `contactId` | uuid \| null | `null` for the collective contact. |
| `contactName` | string | Recipient/invoicing party. |
| `totalAmount` | number | Total (may include tax). |
| `openAmount` | number \| null | Still-unpaid amount. May be `null` (drafts, non-invoice types). |
| `currency` | enum | Only `EUR`. |
| `archived` | boolean | Archived flag in Lexware. |

### Payment (payments endpoint)

| Field | Type | Meaning |
|-------|------|---------|
| `openAmount` | number **or string** | Remaining open amount, always positive. Seen as `200.00`, `0.0`, and quoted `"1337.00"`. |
| `currency` | enum | Always `EUR`. |
| `paymentStatus` | enum | `balanced`, `openRevenue`, `openExpense`. Relative to voucher type: unbalanced sales credit note = `openRevenue`; unbalanced purchase credit note = `openExpense`. |
| `voucherType` | enum | `salesinvoice`, `salescreditnote`, `purchaseinvoice`, `purchasecreditnote`, `invoice`, `downpaymentinvoice`, `creditnote`. |
| `voucherStatus` | enum | `open`, `paid`, `paidoff`, `voided`, `transferred`, `sepadebit`. |
| `paidDate` | dateTime | Date of last payment; only present when status `paid` or `paidoff`. |
| `paymentItems` | list | Individual postings — see below. |

**paymentItems** object: `paymentItemType` enum ∈ {`partPaymentFinancialTransaction` (bank),
`partPaymentCreditNote` (credit note), `partPaymentCashBox` (cash box), `manualPayment` (private
deposit), `cashDiscount` ("Skonto"), `dunningCosts`, `currencyConversion`, `irrecoverableReceivable`
(uncollectible debt)}; `postingDate` (dateTime); `amount` (number, positive); `currency` (`EUR`).

### Payment condition (payment-conditions endpoint)

| Field | Type | Meaning |
|-------|------|---------|
| `id` | uuid | Payment-condition id. |
| `organizationDefault` | boolean | `true` for exactly one (the user default). |
| `paymentTermLabelTemplate` | string | Note text; may hold `{...}` variables like `{discountRange}`/`{paymentRange}`. Read-only. |
| `paymentTermDuration` | integer | Days until payment is due. |
| `paymentDiscountConditions` | object | Optional. `discountPercentage` (number, ≤2 decimals), `discountRange` (integer days the discount is valid). |

### Posting category (posting-categories endpoint)

| Field | Type | Meaning |
|-------|------|---------|
| `id` | uuid | Category id (used as `voucherItems[].categoryId`). |
| `name` | string | Category name (German). |
| `type` | string | `income` (revenue vouchers) or `outgo` (expense vouchers). |
| `contactRequired` | boolean | Whether a referenced contact is mandatory for this category. |
| `splitAllowed` | boolean | Whether items with different tax rates (e.g. 7% + 19%) are allowed. |
| `groupName` | string | Top-level parent category. |

### Well-known categoryIds (from docs; NOT exhaustive — use /v1/posting-categories)

Sales (`salesinvoice`/`salescreditnote`): Warenverkäufe `8f8664a8-fd86-11e1-a21f-0800200c9a66`,
Dienstleistungen `8f8664a0-fd86-11e1-a21f-0800200c9a66`, Einnahmen `8f8664a1-fd86-11e1-a21f-0800200c9a66`,
Innergemeinschaftliche Lieferung `9075a4e3-66de-4795-a016-3889feca0d20`, Fremdleistungen §13b
`380a20cb-d04c-426e-b49c-84c22adfa362`, Ausfuhrlieferungen an Drittländer `93d24c20-ea84-424e-a731-5e1b78d1e6a9`,
Dienstleistungen an Drittländer `ef5b1a6e-f690-4004-9a19-91276348894f`, Einnahmen als Kleinunternehmer
`f5c7fee8-f184-4e7a-ab04-8f7e7ad6c207`.
Distance sales (B2C EU): Fernverkauf `7c112b66-0565-479c-bc18-5845e080880a`, Elektronische Dienstleistungen
`d73b880f-c24a-41ea-a862-18d90e1c3d82`, Fernverkauf in EU-Land steuerpflichtig `4ebd965a-7126-416c-9d8c-a5c9366ee473`,
Elektronische Dienstleistung in EU-Land steuerpflichtig `7ecea006-844c-4c98-a02d-aa3142640dd5`.
Purchase (`purchaseinvoice`/`purchasecreditnote`): Reise Mitarbeiter `cf03a2b0-f838-474f-ac5e-67adb9b830c7`,
Reisen (Selbständige) `efa82f49-fd85-11e1-a21f-0800200c9a66`, Übernachtung Mitarbeiter
`b99b667f-bfee-41b9-8ec0-cee308bdacfd`, Übernachtungskosten (Selbständige) `f9f05694-fd89-11e1-a21f-0800200c9a66`,
Verpflegungsmehraufw. Mitarbeiter `353e8c93-5f69-4476-887f-d48734ee2cc7`, Verpflegungsmehraufwendungen
(Selbständige) `9fb5e4b0-94ae-47f3-804f-5ed00e4aceb6`.

---

## Gotchas

- **Two different status vocabularies.** The **vouchers** endpoint's `voucherStatus` = {`blank`, `open`,
  `paid`, `paidoff`, `voided`, `transferred`, `sepadebit`, `unchecked`} (billing state; only `open` &
  `unchecked` writeable). The **voucherlist** endpoint's `voucherStatus` = {`draft`, `open`, `paid`,
  `paidoff`, `voided`, `transferred`, `sepadebit`, `overdue`, `accepted`, `rejected`, `unchecked`}
  (workflow state; adds `draft`, `overdue`, `accepted`, `rejected`, drops `blank`). Do not assume they
  are the same enum. There is **no `open`/`paid`/`overdue`-only bookkeeping filter on the vouchers
  endpoint** — you must go through voucherlist.
- **`overdue` is a transient/computed status, not stored.** It **cannot be combined** with other status
  filters in a voucherlist query. And filtering for `open` or `sepadebit` will *also* surface items whose
  `dueDate` is in the past as `overdue`. So "overdue" = derive it yourself from `open`/`sepadebit` +
  `dueDate < today`, or query `voucherStatus=overdue` alone.
- **`draft` vs finalized.** A `draft` (voucherlist) / editable voucher is not booked; its `openAmount`
  may be `null`. The payments endpoint **errors** for draft vouchers and for quotations.
- **voucherlist filters `voucherType` AND `voucherStatus` are both MANDATORY.** Use the literal `any`
  to match all. Both accept comma-separated lists (e.g. `voucherType=purchaseinvoice,invoice`).
- **`type` (vouchers) ≠ `voucherType` (voucherlist).** vouchers `type` has only 4 values; voucherlist
  `voucherType` has 10 (adds `invoice`, `creditnote`, `quotation`, `orderconfirmation`, `deliverynote`,
  `downpaymentinvoice`). The full object for each voucherlist row lives at a *type-specific* endpoint
  (bookkeeping types → vouchers; `invoice` → invoices; `creditnote` → credit-notes; etc.).
- **Money type is inconsistent.** Amounts appear as JSON numbers *and* as quoted strings
  (`"openAmount": "1337.00"`). Also decimals are sometimes trimmed (`99.8`, `20.0`, `0`) despite the
  docs claiming `##.00`. Parse as decimal, accept both number and string, never rely on 2-dp text.
- **Dates: send `yyyy-MM-dd`, receive RFC-3339 datetime.** `voucherDate`/`dueDate`/`shippingDate` are
  sent as bare dates but returned as `2023-06-28T00:00:00.000+02:00` (CET/CEST offset). voucherlist
  date filters (`voucherDateFrom`, `createdDateTo`, …) take `yyyy-MM-dd` and mean a full CET/CEST day.
- **gross vs net.** `taxType` decides whether `voucherItems[].amount` is gross or net.
  `net` + `unchecked` is **prohibited** by the API — either finalize (`open`) or convert to `gross` by
  adding tax to each item.
- **Optimistic locking / 409.** PUT with a stale `version` → HTTP 409 Conflict; must re-GET and merge.
  (Base-facts note mentioned 406; the docs specifically say **409** for vouchers.) POST version, if
  sent, must be `1`.
- **File deletion by omission.** Updating a voucher and leaving out a currently-attached file id
  **permanently deletes** that file. Always round-trip the full `files` array.
- **`useCollectiveContact` vs `contactId`.** If `useCollectiveContact:true`, `contactId` is ignored;
  collective contact shows as `contactName: "Sammellieferant"` / `contactId: null` in voucherlist.
- **Paging window cap = 10,000.** voucherlist `totalElements` maxes at 10,000; exceeding it →
  "Maximum search window size exceeded". Narrow the date range. `size` default 25, max **250** for both
  `vouchers` and `voucherlist`; `page` is 0-based. Sort keys: `voucherDate`, `voucherNumber`,
  `createdDate`, `updatedDate` (`,ASC`/`,DESC`); default `voucherdate DESC`.
- **payment-conditions and posting-categories return bare JSON arrays**, NOT Pageable envelopes —
  different parsing path from voucherlist/vouchers.
- **Payments `openAmount` is always positive**; direction is encoded in `paymentStatus`
  (`openRevenue` vs `openExpense`). `voided` vouchers report as `balanced` with `openAmount: 0`.
- **`paidDate` only present for `paid`/`paidoff`.** Don't rely on it existing for `open`/`transferred`.
- **Valid tax rates depend on voucher type + date.** Bookkeeping vouchers (vouchers endpoint) accept
  `0, 5, 7, 16, 19`. Sales documents (invoices, quotations, order confirmations, credit notes) are
  restricted to the rates valid on the relevant date (Corona 2020: 5%/16% only 2020-07-01..2020-12-31).
  EU distance-sales VAT rates only valid when the org's `distanceSalesPrinciple` (profile endpoint) is
  `DESTINATION` and distance-sales/e-service categories are used.
- **`/v1/vouchers?voucherNumber=` filter is DEPRECATED** — docs explicitly say use voucherlist instead.

---

## What the API refuses to answer directly (compute these — killer-feature material)

The API is per-document and per-page; it exposes no aggregates. A CLI must derive them by paging
voucherlist / payments and summing. High-value derivations:

- **Total open receivables** — sum `openAmount` over voucherlist `voucherType=invoice,salesinvoice` (+
  `downpaymentinvoice`) with `voucherStatus=open,overdue` (and `sepadebit`). No single "how much are
  customers still owing me" number exists.
- **Total open payables** — same for `voucherType=purchaseinvoice` with `voucherStatus=open,overdue`.
- **Overdue buckets / aging report** (0–30 / 31–60 / 61–90 / 90+ days) — must be computed client-side
  from each row's `dueDate` vs today; `overdue` status alone gives no age, and can't be combined with
  other status filters, so you bucket manually.
- **Revenue / expense for a period** — sum `totalAmount` (or gross/net from the full voucher) over
  voucherlist filtered by `voucherDateFrom`/`voucherDateTo`; the API returns rows, never a period total.
  Beware the 10,000-row window and gross-vs-net.
- **Paid-this-month / cash-flow timing** — requires fetching `/v1/payments/{id}` per voucher and summing
  `paymentItems[].amount` by `postingDate`; there is no payments list or date-filtered payments query
  (payments is single-voucher GET only).
- **"Show me all unpaid/overdue invoices" as one list** — needs the mandatory-filter voucherlist call
  plus the `overdue` transient-status handling; not a one-liner in the API.
- **Cash-discount (Skonto) exposure / lost discount** — cross-reference payment-conditions'
  `discountPercentage`/`discountRange` against a voucher's `voucherDate`+`dueDate` and payment postings;
  the API never tells you "you can still take 3% until date X" or "you paid cashDiscount of Y".
- **Split payments reconciliation** — `openAmount` = total − Σ`paymentItems.amount` is implied but you
  must confirm it yourself; partial payments (multiple `manualPayment` items) aren't summarized.
- **Category / group spend breakdown** — group `voucherItems[].amount` by `categoryId`→`groupName`
  (via posting-categories) across many vouchers; no group-by endpoint.
- **Duplicate / near-duplicate vouchers** — only exact `voucherNumber` filter exists (and it's
  deprecated); dedup by amount+date+contact is entirely client-side.
- **Contact-level balance ("what does customer X still owe")** — filter voucherlist by `contactId` and
  sum `openAmount`; no per-contact balance field.

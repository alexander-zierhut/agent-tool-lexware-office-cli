# Invoices — Lexware Office API

Scope: the `invoices` resource (`/v1/invoices`) and its document lifecycle — draft vs. finalized,
line items / totals / tax, the two-step PDF/XML download, XRechnung, plus the sibling endpoints an
invoice CLI cannot avoid: `voucherlist` (the only way to *list/filter* invoices), `payments` (the
only place open/paid amounts and payment history live), and `files` (legacy download).

All JSON below is copied VERBATIM from the official docs (developers.lexware.io, one static Slate
HTML page, fetched 2026-07-18). Real UUIDs/dates/enum values are preserved. Where a doc block was
truncated (`...`), that is noted inline.

Base URL `https://api.lexware.io` (legacy `https://api.lexware.com`/`.io` split — docs use `api.lexware.io`).
Auth header `Authorization: Bearer {accessToken}`. `Content-Type` / `Accept`: `application/json`
(except file upload = `multipart/form-data`, file download = `Accept: */*|application/pdf|application/xml`).

---

## Endpoints

| METHOD | Path | Purpose | Notes / permissions |
|--------|------|---------|---------------------|
| POST | `/v1/invoices` | Create an invoice (draft by default) | Body must NOT contain read-only fields. Returns `201` + `{id, resourceUri, createdDate, updatedDate, version}` only — NOT the full object. |
| POST | `/v1/invoices?finalize=true` | Create + immediately finalize (status `open`) | The ONLY way to finalize. Status can never be changed on an existing invoice via the API. |
| POST | `/v1/invoices?precedingSalesVoucherId={id}[&finalize=true]` | "Pursue" a preceding sales voucher (quotation/order confirmation/delivery note) into an invoice | Invalid pursue chains → `406`. Quotation with alternative/optional line items → `406`. Draft order-confirmation/delivery-note preceding → `406`. |
| GET | `/v1/invoices/{id}` | Retrieve one invoice (full object) | Read. |
| GET | `/v1/invoices/{id}/document` | **DEPRECATED** — render PDF, returns `{documentFileId}` | Use `/file` instead. `406` for draft invoices (no file exists). Needed historically to trigger PDF rendering for API-created `open` invoices. |
| GET | `/v1/invoices/{id}/file` | Download the invoice file (PDF or XML) as binary | Preferred download path for sales vouchers. `Accept` header selects PDF vs XML (see table). Draft → `409`. Unknown id → `404`. |
| — | `{appbaseurl}/permalink/invoices/view/{id}` | Deeplink: view page (browser) | Not a REST call; redirects to voucher list if id unknown. |
| — | `{appbaseurl}/permalink/invoices/edit/{id}` | Deeplink: edit page (browser) | Redirects to view page if invoice not editable. |
| GET | `/v1/voucherlist?voucherType=...&voucherStatus=...[&filters]` | **List / filter invoices** (metadata only) | Invoices have NO own list endpoint. `voucherType` + `voucherStatus` are MANDATORY. Paged. Max 10 000 result window. |
| GET | `/v1/payments/{voucherId}` | Payment status of a voucher: `openAmount`, `paymentStatus`, `paymentItems[]`, `paidDate` | The only source of payment history. Errors for drafts / voucher types without payment info. |
| POST | `/v1/files` | Upload a bookkeeping voucher file (multipart) | Returns `202` + `{id, voucherId}`. `type=voucher`, pdf/jpg/png/xml, max 5 MB. Not for creating sales invoices. |
| GET | `/v1/files/{id}` | **DEPRECATED for sales vouchers** — download a file | Use `/v1/invoices/{id}/file` for invoices. Still used for bookkeeping voucher images. |

There is **no `PUT /v1/invoices/{id}` and no `DELETE`** documented. Invoices are create-only through
the API; you cannot edit or void an existing invoice (draft or open) via the API.

---

## Response examples

### GET /v1/invoices/{id} — full invoice object (Invoices Properties sample)

Docs label: "Sample of an invoice with multiple line items. Fields with no content are displayed
with `null` just for demonstration purposes." (draft invoice, one-time address, 4 line items incl.
a `text` item, ZUGFeRD/XRechnung disabled).

```json
{
   "id":"e9066f04-8cc7-4616-93f8-ac9ecc8479c8",
   "organizationId":"aa93e8a8-2aa3-470b-b914-caad8a255dd8",
   "createdDate":"2023-04-24T08:20:22.528+02:00",
   "updatedDate":"2023-04-24T08:20:22.528+02:00",
   "version":0,
   "language":"de",
   "archived":false,
   "voucherStatus":"draft",
   "voucherNumber":"RE1019",
   "voucherDate":"2023-02-22T00:00:00.000+01:00",
   "dueDate":null,
   "address":{
      "contactId":null,
      "name":"Bike & Ride GmbH & Co. KG",
      "supplement":"Gebäude 10",
      "street":"Musterstraße 42",
      "city":"Freiburg",
      "zip":"79112",
      "countryCode":"DE"
   },
   "xRechnung":null,
   "electronicDocumentProfile":"NONE",
   "lineItems":[
      {
         "id":"97b98491-e953-4dc9-97a9-ae437a8052b4",
         "type":"material",
         "name":"Abus Kabelschloss Primo 590 ",
         "description":"- 9,5 mm starkes, smoke-mattes Spiralkabel mit integrierter Halterlösung zur Befestigung am Sattelklemmbolzen\n- bewährter Qualitäts-Schließzylinder mit praktischem Wendeschlüssel\n- KabelØ: 9,5 mm, Länge: 150 cm",
         "quantity":2,
         "unitName":"Stück",
         "unitPrice":{
            "currency":"EUR",
            "netAmount":13.4,
            "grossAmount":15.95,
            "taxRatePercentage":19
         },
         "discountPercentage":50,
         "lineItemAmount":13.4
      },
      {
         "id":"dc4c805b-7df1-4310-a548-22be4499eb04",
         "type":"service",
         "name":"Aufwändige Montage",
         "description":"Aufwand für arbeitsintensive Montagetätigkeit",
         "quantity":1,
         "unitName":"Stunde",
         "unitPrice":{
            "currency":"EUR",
            "netAmount":8.32,
            "grossAmount":8.9,
            "taxRatePercentage":7
         },
         "discountPercentage":0,
         "lineItemAmount":8.32
      },
      {
         "id":null,
         "type":"custom",
         "name":"Energieriegel Testpaket",
         "description":null,
         "quantity":1,
         "unitName":"Stück",
         "unitPrice":{
            "currency":"EUR",
            "netAmount":5,
            "grossAmount":5,
            "taxRatePercentage":0
         },
         "discountPercentage":0,
         "lineItemAmount":5
      },
      {
         "type":"text",
         "name":"Freitextposition",
         "description":"This item type can contain either a name or a description or both."
      }
   ],
   "totalPrice":{
      "currency":"EUR",
      "totalNetAmount":26.72,
      "totalGrossAmount":29.85,
      "totalTaxAmount":3.13,
      "totalDiscountAbsolute":null,
      "totalDiscountPercentage":null
   },
   "taxAmounts":[
      {
         "taxRatePercentage":0,
         "taxAmount":0,
         "netAmount":5
      },
      {
         "taxRatePercentage":7,
         "taxAmount":0.58,
         "netAmount":8.32
      },
      {
         "taxRatePercentage":19,
         "taxAmount":2.55,
         "netAmount":13.4
      }
   ],
   "taxConditions":{
      "taxType":"net",
      "taxTypeNote":null
   },
   "paymentConditions":{
      "paymentTermLabel":"10 Tage - 3 %, 30 Tage netto",
      "paymentTermLabelTemplate":"{discountRange} Tage -{discount}, {paymentRange} Tage netto",
      "paymentTermDuration":30,
      "paymentDiscountConditions":{
         "discountPercentage":3,
         "discountRange":10
      }
   },
   "shippingConditions":{
      "shippingDate":"2023-04-22T00:00:00.000+02:00",
      "shippingEndDate":null,
      "shippingType":"delivery"
   },
   "closingInvoice":false,
   "claimedGrossAmount":null,
   "downPaymentDeductions":null,
   "recurringTemplateId":null,
   "relatedVouchers":[],
   "printLayoutId": "28c212c4-b6dd-11ee-b80a-dbc65f4ceccf",
   "title":"Rechnung",
   "introduction":"Ihre bestellten Positionen stellen wir Ihnen hiermit in Rechnung",
   "remark":"Vielen Dank für Ihren Einkauf",
   "files":{
      "documentFileId":"75295db7-7e69-4630-befd-a7f4ddfdaa83"
   }
}
```

Note: this sample carries `files.documentFileId` even though `voucherStatus` is `draft` — that is
the docs' illustration; in real life a draft invoice has NO document file (see Gotchas). `files` is
marked **deprecated, will be removed**. `xRechnung` is `null` and `electronicDocumentProfile` is
`"NONE"` here.

### GET /v1/invoices/{id} — second retrieve sample (from "Retrieve an Invoice")

A slightly leaner version of the same invoice (omits `dueDate`, `xRechnung`,
`electronicDocumentProfile`, `closingInvoice`, `files`, etc. — i.e. fields that are `null`/absent for
this draft are simply not shown; the docs render omitted fields inconsistently between the two
samples). Line-item `id` for the `custom` item is absent here rather than `null`.

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
  "voucherNumber": "RE1019",
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
      "description": "- 9,5 mm starkes, smoke-mattes Spiralkabel mit integrierter Halterlösung zur Befestigung am Sattelklemmbolzen\n- bewährter Qualitäts-Schließzylinder mit praktischem Wendeschlüssel\n- KabelØ: 9,5 mm, Länge: 150 cm",
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
    { "taxRatePercentage": 0, "taxAmount": 0, "netAmount": 5 },
    { "taxRatePercentage": 7, "taxAmount": 0.58, "netAmount": 8.32 },
    { "taxRatePercentage": 19, "taxAmount": 2.55, "netAmount": 13.4 }
  ],
  "taxConditions": { "taxType": "net" },
  "paymentConditions": {
    "paymentTermLabel": "10 Tage - 3 %, 30 Tage netto",
    "paymentTermLabelTemplate": "{discountRange} Tage -{discount}, {paymentRange} Tage netto",
    "paymentTermDuration": 30,
    "paymentDiscountConditions": { "discountPercentage": 3, "discountRange": 10 }
  },
  "shippingConditions": {
    "shippingDate": "2023-04-22T00:00:00.000+02:00",
    "shippingType": "delivery"
  },
  "title": "Rechnung",
  "introduction": "Ihre bestellten Positionen stellen wir Ihnen hiermit in Rechnung",
  "remark": "Vielen Dank für Ihren Einkauf"
}
```

(Compacted a few `taxAmounts` / nested objects to single lines for readability; field names, values
and structure are verbatim.)

### POST /v1/invoices — create request

```bash
curl https://api.lexware.io/v1/invoices
-X POST
-H "Authorization: Bearer {accessToken}"
-H "Content-Type: application/json"
-H "Accept: application/json"
-d '
{
 "archived": false,
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
      "name": "Energieriegel Testpaket",
      "quantity": 1,
      "unitName": "Stück",
      "unitPrice": {
        "currency": "EUR",
        "netAmount": 5,
        "taxRatePercentage": 0
      },
      "discountPercentage": 0
    },
    {
      "type": "text",
      "name": "Strukturieren Sie Ihre Belege durch Text-Elemente.",
      "description": "Das hilft beim Verständnis"
    }
  ],
  "totalPrice": {
    "currency": "EUR"
   },
  "taxConditions": {
    "taxType": "net"
  },
  "paymentConditions": {
    "paymentTermLabel": "10 Tage - 3 %, 30 Tage netto",
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
  "title": "Rechnung",
  "introduction": "Ihre bestellten Positionen stellen wir Ihnen hiermit in Rechnung",
  "remark": "Vielen Dank für Ihren Einkauf"
}
'
```

Note the create body sends only writable fields: `totalPrice` has just `currency` (totals are
computed server-side), each `unitPrice` sends `netAmount` (not `grossAmount`, because `taxType=net`),
line items carry no `id`/`lineItemAmount`, and there are no `taxAmounts`, `version`, `voucherNumber`,
`dueDate`, etc. Append `?finalize=true` to the URL to finalize on creation.

### POST /v1/invoices — create response

```json
{
  "id": "e9066f04-8cc7-4616-93f8-ac9ecc8479c8",
  "resourceUri": "https://api.lexware.io/v1/invoices/66196c43-bfee-baf3-4335-d610367059db",
  "createdDate": "2023-06-29T15:15:09.447+02:00",
  "updatedDate": "2023-06-29T15:15:09.447+02:00",
  "version": 1
}
```

Note: create returns an **action-result stub, not the invoice**. To get `voucherNumber`, totals,
`taxAmounts`, `documentFileId`, etc. you must follow up with `GET /v1/invoices/{id}`. (The docs'
sample even has a mismatched `id` vs. `resourceUri` UUID — treat `id` as authoritative.)

### GET /v1/invoices/{id}/document — render PDF (DEPRECATED)

Request:
```bash
curl https://api.lexware.io/v1/invoices/e9066f04-8cc7-4616-93f8-ac9ecc8479c8/document
-X GET
-H "Authorization: Bearer {accessToken}"
-H "Accept: application/json"
```

Response:
```json
{
  "documentFileId": "b26e1d73-19ff-46b1-8929-09d8d73d4167"
}
```

Note: deprecated — prefer `GET /v1/invoices/{id}/file`. Historically this endpoint had a side effect:
"PDF document file rendering must be triggered separately via this endpoint for invoices created
through the API with the status `open`." Draft invoices → `406` (no document file exists). The
returned `documentFileId` is then downloadable via the Files endpoint.

### GET /v1/invoices/{id}/file — download invoice file (binary)

```bash
curl "https://api.lexware.io/v1/invoices/{id}/file"
-X GET
-H "Accept: */*"
-H "Authorization: Bearer {accessToken}"
```

Note: returns the file as **binary** with `200`; `Content-Type` = MIME type, `Content-Length` = size,
`Content-Disposition` = suggested filename. `Accept` header chooses PDF vs XML (see Gotchas table).
Draft invoice → `409`; unknown invoice id → `404`; unsupported media type → `406`.

### POST /v1/files — upload (bookkeeping voucher) + response

```bash
curl https://api.lexware.io/v1/files
-X POST
-H "Authorization: Bearer {accessToken}"
-H "Content-Type: multipart/form-data"
-H "Accept: application/json"
-F "file=@{PathToFile}" -F "type=voucher"
```

```json
{
  "id": "8118c402-1c70-4da1-a9f1-a22f480cc623",
  "voucherId": "1deeb1c1-47d6-43f9-9512-c18dd37826fe"
}
```

Note: `202 Accepted`. Only for **bookkeeping** vouchers (Eingangsbelege) — NOT how you create a
sales invoice. `type=voucher`, formats pdf/jpg/png/xml, max 5 MB. Duplicate detection by content
checksum: an identical re-upload returns the existing `id`/`voucherId` and discards the new file.

### GET /v1/voucherlist — list/filter invoices (the only list endpoint)

Request (open invoices + purchase invoices from a date, comma-separated types):
```bash
curl https://api.lexware.io/v1/voucherlist?voucherType=purchaseinvoice,invoice&voucherStatus=open&voucherDateFrom=2023-03-01
-X GET
-H "Authorization: Bearer {accessToken}"
-H "Accept: application/json"
```

Response (Spring Pageable wrapper; note `openAmount` and `overdue` status):
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

Note: the voucherlist row is the ONLY listing shape — it carries `totalAmount`, `openAmount`,
`dueDate`, `contactId`/`contactName`, but NOT line items or tax detail. `openAmount` may be `null`
(drafts, some voucher types). Second row shows a partially-paid open invoice (`totalAmount 99.8`,
`openAmount 74.8`). Note the sample response's `voucherStatus=overdue` row appears even though the
request filtered `voucherStatus=open` — because `overdue` is a transient status returned for `open`
vouchers whose `dueDate` is in the past (see Gotchas).

### GET /v1/payments/{voucherId} — payment status samples (Payments Properties)

Four samples for different voucher types (verbatim; note `openAmount` sometimes a number, sometimes
a quoted string in these docs):
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

And the "Retrieve payment Information" sample response (note `openAmount` as a quoted string here):
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

### taxConditions — vat-free (Reverse Charge) sample

```json
"taxConditions": {
    "taxType": "constructionService13b",
    "taxTypeNote": "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)"
}
```

### Error responses (invoices use the "regular" error format)

Regular error (the sample's `path` is literally `/v1/invoices`):
```json
{
  "timestamp": "2023-05-11T17:12:31.233+02:00",
  "status": 406,
  "error": "Not Acceptable",
  "path": "/v1/invoices",
  "traceId": "90d78d0777be",
  "message": "Validation failed for request. Please see details list for specific causes.",
  "details": [
    {
      "violation": "NOTNULL",
      "field": "lineItems[0].unitPrice.taxRatePercentage",
      "message": "darf nicht leer sein"
    }
  ]
}
```

Legacy error (used by `contacts`, `files`, `vouchers` — NOT invoices, but you WILL hit it via the
files upload endpoint):
```json
{
  "IssueList": [
    {
      "i18nKey": "missing_entity",
      "source": "company.name",
      "type": "validation_failure",
      "additionalData": null,
      "args": null
    }
  ]
}
```

---

## Key fields

### Top-level invoice
| Field | Type | Meaning |
|-------|------|---------|
| `id` | uuid | Server-generated. Read-only. |
| `organizationId` | uuid | Owning organization. Read-only. |
| `createdDate` / `updatedDate` | dateTime | `yyyy-MM-ddTHH:mm:ss.SSSXXX` (RFC 3339). Read-only. |
| `version` | integer | Optimistic-locking revision. **POST must send `0`** (or omit); increments on change. Read-only in responses. |
| `language` | string | ISO 639-1. `de` (default) or `en`. Affects print doc + default text modules. |
| `archived` | boolean | Whether invoice is only in the archive. (Writable on create per the sample; also read-only per prop table — treat as set-on-create.) |
| `voucherStatus` | enum | `draft` (editable) / `open` (finalized, unpaid or partially paid) / `paid` (fully paid) / `voided` (cancelled). Read-only. |
| `voucherNumber` | string | Consecutive number assigned by Lexware on creation. Read-only. |
| `voucherDate` | dateTime | Invoice date. Writable. |
| `dueDate` | dateTime | When payable before overdue. Read-only (derived from paymentConditions). |
| `address` | object | Recipient. Either `contactId` (existing customer contact) or a one-time address. |
| `xRechnung` | object | `{ buyerReference }` — Leitweg-ID. Only relevant for XRechnung-enabled contacts. |
| `electronicDocumentProfile` | enum | `NONE` (also for drafts & non-invoice vouchers), `EN16931` (ZUGFeRD), `XRechnung`. Read-only. |
| `lineItems` | list | Max **300** items. See below. |
| `totalPrice` | object | Totals (net/gross/tax) + optional total discount. Totals read-only. |
| `taxAmounts` | list | Per-rate breakdown. **Read-only — any submitted value on POST is ignored.** |
| `taxConditions` | object | `taxType` (+ optional `taxSubType`, `taxTypeNote`). |
| `paymentConditions` | object | Payment term label/duration + discount conditions. Org/contact default if omitted. |
| `shippingConditions` | object | `shippingDate`, `shippingEndDate`, `shippingType`. |
| `closingInvoice` | boolean | Is this a Schlussrechnung. Read-only. |
| `claimedGrossAmount` | number | Remaining gross (total gross minus sum of received down payments). Read-only. |
| `downPaymentDeductions` | list | Down payments referenced by a closing invoice. Read-only. |
| `recurringTemplateId` | uuid | Set if deduced from a recurring template, else `null`. |
| `relatedVouchers` | list | `{id, voucherNumber, voucherType}` relations. Read-only. |
| `printLayoutId` | uuid | Optional; org default if omitted. |
| `title` / `introduction` / `remark` | string | Optional header/intro/closing text; org defaults if omitted. `introduction`/`remark` support text formatting. |
| `files` | object | **Deprecated** `{ documentFileId }` — PDF id, created when invoice goes draft→open. Read-only. |

### `taxConditions.taxType` (enum — the pricing pivot)
`net`, `gross`, `vatfree` (Steuerfrei), `intraCommunitySupply` (§13b), `constructionService13b`
(Bauleistungen §13b), `externalService13b` (Fremdleistungen EU §13b), `thirdPartyCountryService`
(Dienstleistungen an Drittländer), `thirdPartyCountryDelivery` (Ausfuhrlieferungen an Drittländer),
`photovoltaicEquipment` (0% PV, from 2023-01). `taxSubType` may be `distanceSales` or
`electronicServices` for EU B2C net/gross vouchers. All vat-free types except `vatfree` require a
referenced contact.

### `lineItems[].type` (enum)
`service` (supply of services, needs referenced `id`), `material` (physical product, needs `id`),
`custom` (no Lexware reference, no `id`), `text` (name and/or description only — informational, no
price). `quantity` up to 4 decimals; `discountPercentage` up to 2 decimals; `lineItemAmount` net or
gross depending on `taxConditions.taxType`, read-only.

### `unitPrice`
`currency` (only `EUR`), `netAmount` (up to 4 dp), `grossAmount` (up to 4 dp), `taxRatePercentage`.
On create send `netAmount` when `taxType != gross`, `grossAmount` when `taxType == gross`.

### `totalPrice`
`currency`; `totalNetAmount` / `totalGrossAmount` / `totalTaxAmount` (read-only, computed);
`totalDiscountAbsolute` / `totalDiscountPercentage` (optional inputs, up to 2 dp).

### `taxAmounts[]` (read-only)
`taxRatePercentage`, `taxAmount`, `netAmount` — one entry per distinct rate.

### `paymentConditions`
`paymentTermLabel` (text), `paymentTermLabelTemplate` (with `{discountRange}` etc. variables,
read-only), `paymentTermDuration` (days), `paymentDiscountConditions` = `{ discountPercentage (2dp),
discountRange (days) }`.

### `shippingConditions.shippingType` (enum)
`service`, `serviceperiod`, `delivery`, `deliveryperiod`, `none`. `shippingDate` required for all but
`none`; `shippingEndDate` required for the two `*period` types and must be ≥ `shippingDate`.

### `address`
`contactId` (uuid, when referencing existing contact — must have role **customer**), `name`
(required when no contact; for a person use `{firstname} {lastname}`), `supplement`, `street`,
`city`, `zip`, `countryCode` (ISO 3166 alpha-2, required when no contact), `contactPerson`
(read-only, primary contact person of the referenced contact).

### Voucherlist row (metadata)
`id`, `voucherType`, `voucherStatus`, `voucherNumber`, `voucherDate`, `createdDate`, `updatedDate`,
`dueDate`, `contactId` (`null` for the Collective Contact "Sammelkunde/-lieferant"), `contactName`,
`totalAmount` (`##.00`), `openAmount` (`##.00`, may be `null`), `currency` (EUR), `archived`.
`voucherType` here uses the wider enum: `salesinvoice, salescreditnote, purchaseinvoice,
purchasecreditnote, invoice, downpaymentinvoice, creditnote, orderconfirmation, quotation,
deliverynote`. `voucherStatus` enum adds transient/other-type states: `draft, open, paid, paidoff,
voided, transferred, sepadebit, overdue, accepted, rejected, unchecked`.

### Payments object
`openAmount` (positive for both revenue and expense), `currency` (EUR), `paymentStatus`
(`balanced` / `openRevenue` / `openExpense`), `voucherType`, `voucherStatus` (`open, paid, paidoff,
voided, transferred, sepadebit`), `paidDate` (only when `paid`/`paidoff`), `paymentItems[]`.
`paymentItems[].paymentItemType` enum: `partPaymentFinancialTransaction`, `partPaymentCreditNote`,
`partPaymentCashBox`, `manualPayment`, `cashDiscount` (Skonto), `dunningCosts`, `currencyConversion`,
`irrecoverableReceivable`. Each item: `postingDate`, `amount` (positive), `currency`.

---

## Gotchas

- **Draft vs. finalized is one-way and set at creation.** POST creates a `draft` by default; add
  `?finalize=true` to create directly as `open`. There is NO API call to finalize an existing draft,
  NO way to change `voucherStatus`, and NO `PUT`/`DELETE` on `/v1/invoices/{id}`. If a CLI wants
  "create then finalize" it must decide at POST time.
- **Create returns a stub, not the invoice.** The `201` body is `{id, resourceUri, createdDate,
  updatedDate, version}`. `voucherNumber`, totals, `taxAmounts`, and the PDF id require a follow-up
  `GET`. (And the docs sample's `id` and `resourceUri` UUIDs don't even match — trust `id`.)
- **PDF/XML is a two-step, and the first step is version-gated.** For a `draft` invoice NO document
  file exists: `/document` → `406`, `/file` → `409`. Only after the invoice is `open` does a file
  exist. Preferred path today: `GET /v1/invoices/{id}/file` (binary) directly. The old path was
  `GET /v1/invoices/{id}/document` → `{documentFileId}` → `GET /v1/files/{documentFileId}`; both
  `/document` and `/v1/files/{id}` are **deprecated for sales vouchers**. The `files.documentFileId`
  field on the invoice object is also deprecated and will be removed.
- **`Accept` header selects the representation for `/file`** (sales-voucher table):
  | document profile | `*/*` | `application/xml` | `application/pdf` |
  |---|---|---|---|
  | XRechnung | `.xml` | `.xml` | `.pdf` |
  | ZUGFeRD | `.pdf` | `404` | `.pdf` |
  | regular PDF | `.pdf` | `404` | `.pdf` |
  So `*/*` returns XML for an XRechnung but PDF for everything else. A ZUGFeRD invoice has its XML
  embedded in the PDF — there is no standalone XML download (`application/xml` → `404`). The XRechnung
  PDF is only a **preview and is NOT a valid e-invoice** — do not send it as one. Other media types →
  `406`.
- **Money is per-line net OR gross depending on `taxType`.** With `taxType=net` send/read `netAmount`
  and net `lineItemAmount`; with `gross`, gross. `totalPrice`/`taxAmounts`/`lineItemAmount` are all
  server-computed and ignored on input. `taxAmounts` sent on POST is silently dropped.
- **`openAmount` typing is inconsistent in the docs** — appears as a JSON number (`200.00`, `0.0`)
  in most samples but as a quoted string (`"1337.00"`) in the payments retrieve sample. Parse
  defensively (accept number or numeric string).
- **`overdue` is a transient, computed status.** It is NOT stored. In voucherlist it surfaces for
  vouchers that are `open`/`sepadebit` with `dueDate` in the past — and it can appear even when you
  filtered for `open`. Critically, **`overdue` cannot be combined with other status values** in the
  `voucherStatus` filter (it must be queried alone).
- **`voucherlist` requires BOTH `voucherType` and `voucherStatus`** (or the literal `any`). Invoices
  created by the API have `voucherType=invoice`; Lexware-UI "sales invoices" are
  `voucherType=salesinvoice` and live on the *vouchers* endpoint, not the invoices endpoint. To list
  every kind of receivable you often need `voucherType=invoice,salesinvoice` (comma-separated).
- **Filter date params are `yyyy-MM-dd` (day granularity, CET/CEST)** — e.g. `voucherDateFrom`,
  `createdDateTo` — whereas object date fields are full RFC-3339 timestamps with offset. Don't mix.
- **Search-string encoding is double-encoded.** `&`, `<`, `>` in `voucherNumber`/name searches must
  be HTML-encoded AND then URL-encoded (e.g. `&` → `%26amp%3B`). Applies to voucherlist/vouchers/
  contacts.
- **Result window cap 10 000.** Paged resources error with "Maximum search window size exceeded"
  beyond 10 000 elements; `totalElements` is capped at 10 000. Max page `size` for voucherlist and
  vouchers is **250** (default 25); `page` is 0-based. Narrow by date to stay under the cap.
- **XRechnung is validated hard at creation.** For an authorities/XRechnung-enabled contact the
  invoice must: `taxType=net`, reference an existing `contactId`, have ≥1 line item, and every
  non-`text` line item needs quantity+unit+name. The contact must have a Leitweg-ID (`buyerReference`)
  and a `vendorNumberAtCustomer`. If `xRechnung` is present, `buyerReference` is mandatory; to force a
  plain invoice for such a contact set `buyerReference` to an empty string. Missing buyer reference/
  vendor number → `406`.
- **Optimistic locking:** POST sends `version:0`; a `PUT` (on the resources that support it — NOT
  invoices) must echo the current `version` or you get `409 Conflict`. Invoices are immutable so this
  mostly bites on `contacts`/`vouchers`.
- **Rate limit 2 req/s → `429`** across ALL endpoints combined (token bucket). Also note `500`'s body
  can literally read `"Internal server error or rate limit exceeded"`, so a 500 may actually be
  throttling. Retry with exponential backoff. `504` (30 s gateway timeout) may mean the request
  *did* succeed — verify before retrying a POST to avoid duplicate invoices.
- **Two error shapes.** invoices/voucherlist/payments use the "regular" error
  (`{timestamp,status,error,path,traceId,message,details[]}` with `details[].field` like
  `lineItems[0].unitPrice.taxRatePercentage`). files/vouchers/contacts use the "legacy" error
  (`{IssueList:[{i18nKey,source,type,...}]}`). A CLI touching both invoices and file upload must
  parse both.
- **Tax rate validity is date-dependent.** Sales vouchers (invoices/quotations/order confirmations/
  credit notes) only accept tax rates valid on the *relevant date* (voucherDate, or shippingDate/
  shippingEndDate depending on `shippingType`). E.g. the 2020 Corona reduction: a relevant date of
  2020-06-25 allows 0/7/19%, 2020-07-01 allows 0/5/16%. Vat-free vouchers require `taxRatePercentage`
  `0`.
- **`contactId: null` in a list = the Collective Contact** (Sammelkunde/Sammellieferant), not a
  missing value.
- **Down-payment / closing invoices are read-only via the API.** You cannot pursue a voucher into a
  closing invoice, and `downPaymentDeductions`/`claimedGrossAmount`/`closingInvoice` are read-only.
  Down payment invoices live on a separate `/v1/down-payment-invoices` endpoint.

---

## What the API refuses to answer directly (compute client-side → killer-feature territory)

The API exposes single vouchers and a thin paged metadata list. Every *portfolio-level* or *derived*
question must be assembled by the CLI:

- **Total open receivables / AR balance.** No aggregate endpoint. Must page `voucherlist`
  (`voucherType=invoice,salesinvoice`, `voucherStatus=open,overdue,sepadebit`) and sum `openAmount`.
- **Overdue amount & aging buckets (0–30 / 31–60 / 61–90 / 90+ days).** `overdue` can't even be
  combined with other statuses in one query, and there's no bucketing. Fetch open invoices, compute
  `today - dueDate` per row, and bucket + sum `openAmount` yourself.
- **Revenue for a period (net vs gross, by tax rate, by month).** No revenue report. Sum
  `totalAmount`/line-item tax breakdown across a date-filtered voucherlist (and remember voucherlist
  gives only `totalAmount`, so per-rate/net figures need a `GET` per invoice or the vouchers data).
- **Days-sales-outstanding / average time-to-pay.** Requires cross-referencing each invoice's
  `voucherDate` with the payment `paidDate` / last `paymentItems[].postingDate` from `/v1/payments`.
- **"Which invoices did customer X pay late / still owe?"** No contact-rollup. Filter voucherlist by
  `contactId`, then per invoice call `/v1/payments/{id}` for the payment timeline.
- **Partial-payment detail.** `voucherlist.openAmount` shows the remaining amount but not *why*
  (Skonto vs partial bank payment vs write-off). Only `/v1/payments/{id}` `paymentItems[]` has the
  breakdown (`cashDiscount`, `irrecoverableReceivable`, etc.) — one call per invoice.
- **Duplicate-invoice / duplicate-contact detection.** No dedup. Must scan and compare
  (contactName+totalAmount+date, or line-item fingerprints) client-side.
- **Quote → order → invoice conversion funnel / lifecycle status.** `relatedVouchers` on a single
  invoice only shows *that* invoice's relations; there's no chain query. Building the funnel means
  walking voucherlist across `quotation`/`orderconfirmation`/`deliverynote`/`invoice` and stitching
  by `relatedVouchers`.
- **Tax/VAT summary for a filing period (USt-Voranmeldung style).** `taxAmounts` exists per invoice
  only. Summing per-rate tax across a period requires a `GET` on every invoice in the range.
- **Cash-flow forecast from `dueDate`.** No forecast endpoint; project from open invoices' `dueDate`
  + `openAmount` yourself.
- **Bulk PDF export.** No batch; loop `GET /v1/invoices/{id}/file` per invoice, throttled to 2 req/s.

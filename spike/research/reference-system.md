# Reference & System — Lexware Office API

Source: <https://developers.lexware.io/docs/> — sections "Articles Endpoint", "Countries Endpoint",
"Files Endpoint", "Print Layouts Endpoint", "Profile Endpoint", "Recurring Templates Endpoint",
"Event Subscriptions Endpoint", plus "Optimistic Locking" and the "Country Codes" FAQ (verbatim,
captured 2026-07).

Base URL `https://api.lexware.io` (legacy `https://api.lexware.com` until Dec 2025). Auth header
`Authorization: Bearer <apiKey>`. `Content-Type: application/json`, `Accept: application/json`
(files upload/download differ — see Files). Rate limit 2 req/s → HTTP 429.

This area groups the "supporting" resources a CLI needs alongside the sales/bookkeeping vouchers:
the **article** catalogue (products/services referenced by line items), **files** (voucher image
upload / e-invoice download), the **profile** (org identity + feature gating), the read-only
**countries** and **print-layouts** lookups, the read-only **recurring-templates** (subscription
invoices), and **event-subscriptions** (the webhook machinery). Articles and event-subscriptions are
read-write; everything else here is read-only over the API.

---

## Endpoints

| METHOD | Path | Purpose | Notes / permissions |
|--------|------|---------|---------------------|
| POST   | `/v1/articles` | Create a product/service article | Body required: `title`, `type`, `unitName`, `price`. New resources start at `version` 0. Returns an **action-result** (`id`, `resourceUri`, `createdDate`, `updatedDate`, `version`), **not** the full article. |
| GET    | `/v1/articles/{id}` | Retrieve one article | Full entity. |
| PUT    | `/v1/articles/{id}` | Update an article | Must send current `version` (optimistic locking → 409 on stale). Returns action-result. |
| DELETE | `/v1/articles/{id}` | Delete an article | **204** on success, **404** if id unknown. (Unlike contacts, articles really can be deleted.) |
| GET    | `/v1/articles?…` | List / filter articles (paged "Pageable") | Filters: `articleNumber`, `gtin`, `type` (AND-combined; each filter at most once). `page`, `size` (max 250). Fixed sort by `title` ASC. |
| GET    | `/v1/countries` | List all known countries | Read-only. Returns a **bare JSON array** (no Pageable wrapper). |
| POST   | `/v1/files` | Upload a voucher file (multipart) | `Content-Type: multipart/form-data`, fields `file=@…` + `type=voucher`. Returns **202** `{id, voucherId}`. Uses **legacy** error handling. |
| GET    | `/v1/files/{id}` | Download a file (binary) | **Deprecated for sales-voucher docs** — use the per-voucher file subresource instead; still valid for bookkeeping voucher docs. `Accept` header selects PDF vs XML for e-invoices. |
| GET    | `/v1/print-layouts` | List print layouts for the org | Read-only, bare array. Needs the `INVOICING_PRO` business feature. One layout may be `default`. |
| GET    | `/v1/profile` | Retrieve connected-account profile | Read-only. Org id, company name, connection info, `taxType`, `businessFeatures`. |
| GET    | `/v1/recurring-templates/{id}` | Retrieve one recurring template | **Read-only** (no POST/PUT/DELETE over the API). Full entity. |
| GET    | `/v1/recurring-templates?…` | List recurring templates (paged) | Read-only. `page`, `size` (max 250), `sort` = `createdDate`/`updatedDate`/`lastExecutionDate`/`nextExecutionDate` `,ASC|DESC` (default `updatedDate,DESC`). Collection rows carry a **reduced** projection (see Gotchas). |
| POST   | `/v1/event-subscriptions` | Subscribe to an event (webhook) | Body: `eventType` + `callbackUrl`. Returns **201** action-result (`id`, `resourceUri`, `version`) + `Location` header. Duplicate (same type+url) → **409**. HEAD sent to callbackUrl to check SSL → **406** if it fails. |
| GET    | `/v1/event-subscriptions/{subscriptionId}` | Retrieve one subscription | Returns entity keyed by `subscriptionId` (no `version`). |
| GET    | `/v1/event-subscriptions` | Retrieve all subscriptions | `{ "content": [ … ] }` — **content-wrapped but WITHOUT paging metadata**. |
| DELETE | `/v1/event-subscriptions/{subscriptionId}` | Delete a subscription | **204** on success. "Updating" a subscription = delete then recreate. |
| —      | `{appbaseurl}/permalink/files/view` | Deeplink to uploaded bookkeeping files (browser) | Not REST. |
| —      | `{appbaseurl}/permalink/recurring-templates/edit/{id}` | Deeplink to edit a recurring template (browser) | Not REST. No standalone view page (redirects to voucher list on unknown id). |
| POST   | *(your `callbackUrl`)* | Lexware → you: webhook callback | Lexware POSTs the callback JSON to your URL; you must answer 2xx. Signed via `X-Lxo-Signature` (RSA-SHA512, base64). |

---

## Response examples

### GET `/v1/articles/{id}` — full "Article Properties" sample (all fields populated)

```json
{
  "id": "eb46d328-e1dc-11ee-8444-2fadfc15a567",
  "organizationId": "9e700f44-0c55-11ef-ac31-8f7c36d1b6e2",
  "createdDate": "2023-09-21T17:46:40.629+02:00",
  "updatedDate": "2024-05-03T12:21:32.120+02:00",
  "archived": false,
  "title": "Lexware buchhaltung Premium 2024",
  "description": "Monatsabonnement. Mehrplatzsystem zur Buchhaltung. Produkt vom Marktführer. PC Aktivierungscode per Email",
  "type": "PRODUCT",
  "articleNumber": "LXW-BUHA-2024-001",
  "gtin": "9783648170632",
  "note": "Interne Notiz",
  "unitName": "Download-Code",
  "price": {
    "netPrice": 61.90,
    "grossPrice": 73.66,
    "leadingPrice": "NET",
    "taxRate": 19
  },
  "version": 2
}
```

Note: money is plain JSON numbers with no explicit currency (EUR implied). `type` ∈ `PRODUCT` | `SERVICE`.
`price.taxRate` documented values (as of March 2024) are `0`, `7`, `19`.

### POST `/v1/articles` — action-result on create

```json
{
    "id": "f5d5e4c2-e20a-11ee-9cde-7789c0d1fa1c",
    "resourceUri": "https://api.lexware.io/v1/articles/f5d5e4c2-e20a-11ee-9cde-7789c0d1fa1c",
    "createdDate": "2024-03-14T14:58:10.320+01:00",
    "updatedDate": "2024-03-14T14:58:10.320+01:00",
    "version": 0
}
```

Note: create/update return this action-result shape (NOT the article). New resources get `version: 0`.

### GET `/v1/articles/{id}` — retrieve response (note: no `organizationId`/`createdDate`/`updatedDate`/`archived` here)

```json
{
  "id": "eb46d328-e1dc-11ee-8444-2fadfc15a567",
  "title": "Lexware buchhaltung Premium 2024",
  "description": "Monatsabonnement. Mehrplatzsystem zur Buchhaltung. Produkt vom Marktführer. PC Aktivierungscode per Email",
  "type": "PRODUCT",
  "articleNumber": "LXW-BUHA-2024-001",
  "gtin": "9783648170632",
  "note": "Interne Notiz",
  "unitName": "Download-Code",
  "price": {
    "netPrice": 61.90,
    "grossPrice": 73.66,
    "leadingPrice": "NET",
    "taxRate": 19
  },
  "version": 0
}
```

Note: the docs' retrieve sample omits several read-only fields that the Properties sample shows
(`organizationId`, `createdDate`, `updatedDate`, `archived`). Treat the field set as best-effort; parse leniently.

### PUT `/v1/articles/{id}` — action-result on update

```json
{
  "id": "eb46d328-e1dc-11ee-8444-2fadfc15a567",
  "resourceUri": "https://api.lexware.io/v1/articles/eb46d328-e1dc-11ee-8444-2fadfc15a567",
  "createdDate": "2024-03-14T14:58:10.320+01:00",
  "updatedDate": "2024-04-29T16:12:09.512+02:00",
  "version": 2
}
```

### GET `/v1/articles?page=0` — list (Pageable wrapper)

```json
{
    "content": [
      {
        "id": "eb46d328-e1dc-11ee-8444-2fadfc15a567",
        "title": "Lexware buchhaltung Premium 2024",
        "description": "Monatsabonnement. Mehrplatzsystem zur Buchhaltung. Produkt vom Marktführer. PC Aktivierungscode per Email",
        "type": "PRODUCT",
        "articleNumber": "LXW-BUHA-2024-001",
        "gtin": "9783648170632",
        "note": "Interne Notiz",
        "unitName": "Download-Code",
        "price": {
          "netPrice": 61.90,
          "grossPrice": 73.66,
          "leadingPrice": "NET",
          "taxRate": 19
        },
        "version": 1
      },
      {
        "id": "f7e14ba6-e2ac-11ee-96c1-3b561501789e",
        "title": "Lexware warenwirtschaft Premium 2024",
        "description": "Monatsabonnement. Mehrplatzsystem zur kompletten Warenwirtschaft. Produkt vom Marktführer. PC Aktivierungscode per Email",
        "type": "PRODUCT",
        "articleNumber": "LXW-WAWI-2024-001",
        "gtin": "9783648170779",
        "note": "Interne Notiz",
        "unitName": "Download-Code",
        "price": {
          "netPrice": 61.90,
          "grossPrice": 73.66,
          "leadingPrice": "NET",
          "taxRate": 19
        },
        "version": 3
      }
    ],
    "totalPages": 1,
    "totalElements": 2,
    "last": true,
    "sort": [
      {
          "direction": "ASC",
          "property": "title",
          "ignoreCase": false,
          "nullHandling": "NATIVE",
          "ascending": true
      }
    ],
    "size": 25,
    "number": 0,
    "first": true,
    "numberOfElements": 2
}
```

Note: this is the canonical Spring "Pageable" wrapper (`content`, `totalPages`, `totalElements`,
`size`, `number`, `first`, `last`, `numberOfElements`, `sort[]`). Article list is always sorted `title` ASC.

### GET `/v1/countries` — bare array

```json
[
    {
        "countryCode": "DE",
        "countryNameDE": "Deutschland",
        "countryNameEN": "Germany",
        "taxClassification": "de"
    },
    {
        "countryCode": "FR",
        "countryNameDE": "Frankreich",
        "countryNameEN": "France",
        "taxClassification": "intraCommunity"
    },
    {
        "countryCode": "US",
        "countryNameDE": "Vereinigte Staaten von Amerika",
        "countryNameEN": "United States",
        "taxClassification": "thirdPartyCountry"
    }
]
```

Note: NOT paged — a plain array. `taxClassification` ∈ `de` | `intraCommunity` | `thirdPartyCountry`.
Codes are ISO 3166 alpha2, plus extended forms like `ES_CN` (Canary Islands), `GR_69` (Mount Athos).

### GET `/v1/print-layouts` — bare array

```json
[
    {
        "id": "0dda299a-b5db-11ee-93dd-1755da51b5dc",
        "name": "Standard",
        "default": true
    },
    {
        "id": "1ecf228c-b5db-11ee-bdaa-bbbd077b15cd",
        "name": "Alternate layout",
        "default": false
    }
]
```

Note: exactly one entry may have `default: true`. Requires the `INVOICING_PRO` business feature.

### GET `/v1/profile` — profile response

```json
{
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "companyName": "Testfirma GmbH",
  "created": {
    "userId": "1aea5501-3f3e-403d-8492-2dad03016289",
    "userName": "Frau Erika Musterfrau",
    "userEmail": "erika.musterfrau@testfirma.de",
    "date": "2017-01-03T13:15:45.000+01:00"
  },
  "connectionId": "3dea098a-fae5-4458-a85c-f97965966c25",
  "features": [
    "cashbox"
  ],
  "businessFeatures": [
    "INVOICING",
    "INVOICING_PRO",
    "BOOKKEEPING"
  ],
  "subscriptionStatus": "active",
  "taxType": "net",
  "smallBusiness": false
}
```

Note: **the sample and the docs' property table diverge.** The table documents
`organizationId`, `companyName`, `created`, `connectionId`, `taxType`, `distanceSalesPrinciple`,
`businessFeatures`, `smallBusiness` — but the JSON sample **omits** `distanceSalesPrinciple` and
**adds two undocumented fields**: `features` (e.g. `["cashbox"]`) and `subscriptionStatus`
(e.g. `"active"`). Parse leniently. `taxType` ∈ `net` | `gross` | `vatfree`.

### POST `/v1/files` — upload response (HTTP 202)

```json
{
  "id": "8118c402-1c70-4da1-a9f1-a22f480cc623",
  "voucherId": "1deeb1c1-47d6-43f9-9512-c18dd37826fe"
}
```

Note: 202 Accepted + the file id and the id of the auto-created voucher. Same file (by content
checksum) uploaded twice returns the **existing** ids and discards the new upload.

### Event subscription — "Event Subscriptions Properties" sample (entity shape)

```json
{
  "subscriptionId": "4d43ad14-671d-4e0c-fd4b-2fd8cc117eff",
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "createdDate": "2023-04-11T12:15:00.000+02:00",
  "eventType": "contact.changed",
  "callbackUrl": "https://example.org/webhook"
}
```

### Webhook callback payload (Lexware → your `callbackUrl`, HTTP POST)

```json
{
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "eventType": "contact.changed",
  "resourceId": "4d43ad14-671d-4e0c-fd4b-2fd8cc117eff",
  "eventDate": "2023-04-11T12:30:00.000+02:00"
}
```

Note: this is the entire payload — it carries only the `resourceId`, never the changed entity.
You must GET the resource yourself. Verify authenticity via the `X-Lxo-Signature` header
(RSA-SHA512 signature of the whitespace-free JSON body, base64-encoded; verify with Lexware's public key).
For `token.revoked`, `resourceId` is the `connectionId` (from the profile endpoint), not a voucher id.

### POST `/v1/event-subscriptions` — create response (HTTP 201, action-result)

```json
{
    "id": "49aa2f76-c51a-4df3-ae83-3a103d781494",
    "resourceUri": "https://api.lexware.io/v1/event-subscriptions/49aa2f76-c51a-4df3-ae83-3a103d781494",
    "createdDate": "2023-04-11T12:20:00.000+02:00",
    "updatedDate": "2023-04-11T12:20:00.000+02:00",
    "version": 0
}
```

Note: **naming mismatch** — create returns `id` (+ `resourceUri`, `version`); GET returns the same
resource keyed as `subscriptionId` with no `version`. The `Location` header also carries the resource URL.

### GET `/v1/event-subscriptions/{subscriptionId}` — retrieve one

```json
{
    "subscriptionId": "49aa2f76-c51a-4df3-ae83-3a103d781494",
    "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
    "createdDate": "2023-04-11T12:20:00.000+02:00",
    "eventType": "contact.changed",
    "callbackUrl": "https://example.org/webhook"
}
```

### GET `/v1/event-subscriptions` — retrieve all (content-wrapped, no paging metadata)

```json
{
    "content": [
        {
            "subscriptionId": "49aa2f76-c51a-4df3-ae83-3a103d781494",
            "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
            "createdDate": "2023-04-11T12:20:00.000+02:00",
            "eventType": "contact.changed",
            "callbackUrl": "https://example.org/webhook"
        }
    ]
}
```

Note: wrapped in `content` but WITHOUT `totalPages`/`size`/`number`/etc. — it is not a real Pageable.

### GET `/v1/recurring-templates/{id}` — full "Recurring Template Properties" sample

Docs caveat: *"Fields with no content are displayed with `null` just for demonstration purposes."*

```json
{
  "id": "ac1d66a8-6d59-408b-9413-d56b1db7946f",
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "createdDate": "2023-02-10T09:00:00.000+01:00",
  "updatedDate": "2023-02-10T09:00:00.000+01:00",
  "version": 0,
  "language": "de",
  "archived": false,
  "address": {
    "contactId": "464f4881-7a8c-4dc4-87de-7c6fd9a506b8",
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
      "id": null,
      "type": "custom",
      "name": "Energieriegel Testpaket",
      "description": null,
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
    },
    {
      "type": "text",
      "name": "Freitextposition",
      "description": "This item type can contain either a name or a description or both."
    }
  ],
  "totalPrice": {
    "currency": "EUR",
    "totalNetAmount": 26.72,
    "totalGrossAmount": 29.85,
    "totalTaxAmount": 3.13,
    "totalDiscountAbsolute": null,
    "totalDiscountPercentage": null
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
    "taxType": "net",
    "taxTypeNote": null
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
  "title": "Rechnung",
  "introduction": "Ihre bestellten Positionen stellen wir Ihnen hiermit in Rechnung",
  "remark": "Vielen Dank für Ihren Einkauf",
  "recurringTemplateSettings": {
    "id": "9c5b8bde-7d36-49e8-af5c-4fbe7dc9fa01",
    "startDate": "2023-03-01",
    "endDate": "2023-06-30",
    "finalize": true,
    "shippingType": "service",
    "retroactiveInvoice": false,
    "executionInterval": "MONTHLY",
    "nextExecutionDate": "2023-03-01",
    "lastExecutionDate": null,
    "lastExecutionFailed": false,
    "lastExecutionErrorMessage": null,
    "executionStatus": "ACTIVE"
  }
}
```

Note: a recurring template mirrors an invoice **minus** `voucherStatus`, `voucherNumber`,
`voucherDate`, `dueDate`, `shippingConditions`, and `files` — those only exist on the invoices it
generates. All the recurring-specific state lives in `recurringTemplateSettings`. Dates there are
short ISO (`yyyy-MM-dd`, no time).

There is also a small verbatim fragment in the docs showing a vat-free `taxConditions` block:

```json
"taxConditions": {
    "taxType": "constructionService13b",
    "taxTypeNote": "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)"
}
```

### GET `/v1/recurring-templates/{id}` — retrieve sample (settings TRUNCATED in the docs)

```json
{
    "id": "ac1d66a8-6d59-408b-9413-d56b1db7946f",
    "organizationId": "a3d94eb4-98bc-429e-b7ad-17f1a8463af9",
    "createdDate": "2023-02-10T14:29:03.114+01:00",
    "updatedDate": "2023-02-10T14:29:03.143+01:00",
    "version": 1,
    "language": "de",
    "archived": false,
    "address": {
        "contactId": "df315523-1e92-473a-9d00-052212da84f8",
        "name": "Haufe-Lexware GmbH & Co. KG",
        "street": "Munzingerstraße 8",
        "city": "Freiburg",
        "zip": "79111",
        "countryCode": "DE"
    },
    "lineItems": [
        {
            "type": "custom",
            "name": "Schulung",
            "quantity": 6,
            "unitName": "Stunde",
            "unitPrice": {
                "currency": "EUR",
                "netAmount": 100.84,
                "grossAmount": 120,
                "taxRatePercentage": 19
            },
            "discountPercentage": 0,
            "lineItemAmount": 720.00
        }
    ],
    "totalPrice": {
        "currency": "EUR",
        "totalNetAmount": 605.04,
        "totalGrossAmount": 720,
        "totalTaxAmount": 114.96
    },
    "taxAmounts": [
        {
            "taxRatePercentage": 19,
            "taxAmount": 114.96,
            "netAmount": 605.04
        }
    ],
    "taxConditions": {
        "taxType": "gross"
    },
    "paymentConditions": {
        "paymentTermLabel": "Zahlbar sofort, rein netto",
        "paymentTermLabelTemplate": "Zahlbar sofort, rein netto",
        "paymentTermDuration": 0
    },
    "introduction": "Unsere Lieferungen/Leistungen stellen wir Ihnen wie folgt in Rechnung.",
    "remark": "Vielen Dank für die gute Zusammenarbeit.",
    "title": "Rechnung",
    "recurringTemplateSettings": {
        ....
    }
}
```

Note: the docs literally print `"recurringTemplateSettings": { .... }` here — the settings object is
**truncated in the source docs**. Use the full-properties sample (above) or the collection sample
(below) for the real settings shape.

### GET `/v1/recurring-templates?page=0&size=25&sort=createdDate,DESC` — collection (reduced projection)

```json
{
    "content": [
        {
            "id": "cab021e5-91d3-4e93-a696-56b7f2417547",
            "organizationId": "a3d94eb4-98bc-429e-b7ad-17f1a8463af9",
            "title": "Rechnung",
            "createdDate": "2023-02-10T14:35:40.642+01:00",
            "updatedDate": "2023-02-10T14:36:49.741+01:00",
            "address": {
                "contactId": "464f4881-7a8c-4dc4-87de-7c6fd9a506b8",
                "name": "Bike & Ride GmbH & Co. KG"
            },
            "totalPrice": {
                "currency": "EUR",
                "totalNetAmount": 251.26,
                "totalGrossAmount": 299
            },
            "paymentConditions": {
                "paymentTermLabel": "10 Tage abzüglich 2 % Skonto",
                "paymentTermLabelTemplate": "{paymentRange} Tage abzüglich {discount} Skonto",
                "paymentTermDuration": 10,
                "paymentDiscountConditions": {
                    "discountPercentage": 2,
                    "discountRange": 10
                }
            },
            "recurringTemplateSettings": {
                "id": "615a8db3-bce1-4e11-8302-328fcbacd613",
                "startDate": "2023-04-01",
                "endDate": "2024-04-01",
                "finalize": false,
                "shippingType": "serviceperiod",
                "retroactiveInvoice": false,
                "executionInterval": "QUARTERLY",
                "nextExecutionDate": null,
                "lastExecutionDate": null,
                "lastExecutionFailed": false,
                "executionStatus": "PAUSED"
            }
        },
        {
            "id": "ac1d66a8-6d59-408b-9413-d56b1db7946f",
            "organizationId": "a3d94eb4-98bc-429e-b7ad-17f1a8463af9",
            "title": "Rechnung",
            "createdDate": "2023-02-10T14:29:03.114+01:00",
            "updatedDate": "2023-02-10T14:29:03.143+01:00",
            "address": {
                "contactId": "df315523-1e92-473a-9d00-052212da84f8",
                "name": "Haufe-Lexware GmbH & Co. KG"
            },
            "totalPrice": {
                "currency": "EUR",
                "totalNetAmount": 605.04,
                "totalGrossAmount": 720
            },
            "paymentConditions": {
                "paymentTermLabel": "Zahlbar sofort, rein netto",
                "paymentTermLabelTemplate": "Zahlbar sofort, rein netto",
                "paymentTermDuration": 0
            },
            "recurringTemplateSettings": {
                "id": "9c5b8bde-7d36-49e8-af5c-4fbe7dc9fa01",
                "startDate": "2023-03-01",
                "endDate": "2023-06-30",
                "finalize": true,
                "shippingType": "service",
                "retroactiveInvoice": false,
                "executionInterval": "MONTHLY",
                "nextExecutionDate": "2023-03-01",
                "lastExecutionDate": null,
                "lastExecutionFailed": false,
                "executionStatus": "ACTIVE"
            }
        }
    ],
    "first": true,
    "last": true,
    "totalPages": 1,
    "totalElements": 2,
    "numberOfElements": 2,
    "size": 25,
    "number": 0,
    "sort": [
        {
            "property": "createdDate",
            "direction": "DESC",
            "ignoreCase": false,
            "nullHandling": "NATIVE",
            "ascending": false
        }
    ]
}
```

Note: the collection rows carry ONLY a reduced projection — `address` shrinks to `{contactId, name}`,
`totalPrice` drops `totalTaxAmount`/discounts, and there are **no** `lineItems`, `taxAmounts`,
`taxConditions`, `introduction`, `remark`. The full `recurringTemplateSettings` IS included. To get
line items you must GET the individual template.

---

## Key fields

### Article
- `type` — enum, `PRODUCT` | `SERVICE`. Required on create.
- `price.leadingPrice` — enum `NET` | `GROSS`. Determines which of `netPrice`/`grossPrice` you supply;
  the other is computed from the leading price + `taxRate`. On read it reflects the last-set leading price.
- `price.netPrice` — read-only when `leadingPrice=GROSS`; required when `leadingPrice=NET`.
- `price.grossPrice` — read-only when `leadingPrice=NET`; required when `leadingPrice=GROSS`.
- `price.taxRate` — number; documented `0` / `7` / `19` (as of March 2024). Not a percentage-of-100 fraction — literal 19 means 19 %.
- `gtin` — validated against GTIN-8/12/13/14 formats if given.
- `articleNumber` — user-assigned; the `articleNumber` filter matches it exactly.
- `unitName` — free text; required on create.
- `archived`, `version`, `id`, `organizationId`, `createdDate`, `updatedDate` — read-only.

### Profile
- `organizationId` (uuid), `companyName` (string), `connectionId` (uuid = the API connection).
- `created` — object `{ userId, userName, userEmail, date }` (who connected + when).
- `taxType` — enum `net` | `gross` | `vatfree`.
- `distanceSalesPrinciple` — enum `ORIGIN` | `DESTINATION` (documented; **absent** from the JSON sample when unset).
- `businessFeatures` — list; possible values `INVOICING`, `INVOICING_PRO`, `BOOKKEEPING`. Capability gate.
- `smallBusiness` — boolean (Kleinunternehmer §19 UStG).
- `features` — list, undocumented (e.g. `["cashbox"]`); `subscriptionStatus` — string, undocumented (e.g. `"active"`).

### Country
- `countryCode` — ISO 3166 alpha2 (`DE`, `FR`, `US`), plus extended `ES_CN`, `GR_69` for divergent-tax regions.
- `countryNameEN` / `countryNameDE` — display names.
- `taxClassification` — enum `de` | `intraCommunity` | `thirdPartyCountry` (current classification; can change over time).

### Print layout
- `id` (uuid), `name` (string), `default` (boolean — at most one true for the org).

### File upload / download
- Upload form fields: `file` (binary) + `type` (`voucher`). Upload response: `id` (file id) + `voucherId` (auto-created voucher).
- `type=voucher`: formats `pdf, jpg, png, xml`; max **5 MB**.
- Download selects representation by `Accept`: `*/*` → default (PDF), `application/xml` → e-invoice XML (only if a separate XML exists), `application/pdf`/`image/png`/`image/jpeg` as appropriate.

### Recurring template
- Header: `id`, `organizationId`, `createdDate`, `updatedDate`, `version` (all read-only), `language`
  (`de` default | `en`), `archived`, `title`, `introduction`, `remark`.
- `address` — `{ contactId, name, supplement?, street, city, zip, countryCode, contactPerson? }`;
  always references an existing contact (`contactId`).
- `lineItems[].type` — enum `service` | `material` | `custom` | `text` (max 300 items). `text` items
  carry only name/description. `id` present only when referencing a stored product/service.
- `lineItems[].unitPrice` — `{ currency (EUR only), netAmount, grossAmount, taxRatePercentage }`
  (amounts up to 4 decimals). `quantity` up to 4 decimals; `discountPercentage` up to 2 decimals.
- `lineItemAmount` — read-only; net or gross depending on `taxConditions.taxType`.
- `totalPrice` — `{ currency, totalNetAmount, totalGrossAmount, totalTaxAmount (read-only),
  totalDiscountAbsolute?, totalDiscountPercentage? }`.
- `taxAmounts[]` — read-only per-rate breakdown `{ taxRatePercentage, taxAmount, netAmount }`.
- `taxConditions.taxType` — enum: `net`, `gross`, `vatfree`, `intraCommunitySupply`,
  `constructionService13b`, `externalService13b`, `thirdPartyCountryService`,
  `thirdPartyCountryDelivery`, `photovoltaicEquipment`. Optional `taxSubType` (`distanceSales` /
  `electronicServices`) and `taxTypeNote`.
- `paymentConditions` — `{ paymentTermLabel, paymentTermLabelTemplate (read-only, has {vars}),
  paymentTermDuration (days), paymentDiscountConditions{ discountPercentage, discountRange (days) } }`.
- `recurringTemplateSettings` (entire object read-only):
  - `startDate` / `endDate` — short ISO `yyyy-MM-dd`. `startDate` null ⇒ template is PAUSED.
  - `finalize` — boolean: false ⇒ generated invoices are `draft` (editable); true ⇒ `open`
    (finalized) **and automatically emailed to the customer** on creation.
  - `shippingType` — enum `service` | `serviceperiod` | `delivery` | `deliveryperiod` | `none`.
  - `executionInterval` — enum `WEEKLY` | `BIWEEKLY` | `MONTHLY` | `QUARTERLY` | `BIANNUALLY` | `ANNUALLY`.
  - `nextExecutionDate` / `lastExecutionDate` — short ISO, read-only; null when never run / paused.
  - `lastExecutionFailed` (bool) + `lastExecutionErrorMessage` (string) — last-run diagnostics.
  - `retroactiveInvoice` — bool, read-only.
  - `executionStatus` — enum `ACTIVE` | `PAUSED` | `ENDED`. **No error state** (a failed run stays ACTIVE).

### Event subscription
- Entity: `subscriptionId`, `organizationId`, `createdDate`, `eventType`, `callbackUrl` (all read-only except the two you set).
- Create action-result uses `id` (+ `resourceUri`, `version`) instead of `subscriptionId`.
- `eventType` — lower-case `resource.event` combined key (see the Event Types list below).
- Callback payload: `organizationId`, `eventType`, `resourceId`, `eventDate`.

### Event types (verbatim list of subscribable `eventType` values)
`article.created`, `article.changed`, `article.deleted`,
`contact.created`, `contact.changed`, `contact.deleted`,
`credit-note.created`, `credit-note.changed`, `credit-note.deleted`, `credit-note.status.changed`,
`delivery-note.created`, `delivery-note.changed`, `delivery-note.deleted`, `delivery-note.status.changed`,
`down-payment-invoice.created`, `down-payment-invoice.changed`, `down-payment-invoice.deleted`, `down-payment-invoice.status.changed`,
`dunning.created`, `dunning.changed`, `dunning.deleted`,
`invoice.created`, `invoice.changed`, `invoice.deleted`, `invoice.status.changed`,
`order-confirmation.created`, `order-confirmation.changed`, `order-confirmation.deleted`, `order-confirmation.status.changed`,
`payment.changed` (fired for credit-notes, invoices, vouchers),
`quotation.created`, `quotation.changed`, `quotation.deleted`, `quotation.status.changed`,
`recurring-template.created`, `recurring-template.changed`, `recurring-template.deleted`,
`token.revoked` (resource = the refresh token/connection; `resourceId` = `connectionId`),
`voucher.created`, `voucher.changed`, `voucher.deleted`, `voucher.status.changed`.

---

## Gotchas

- **Recurring templates are read-only over the API.** No POST/PUT/DELETE — they can only be created or
  edited in the Lexware web app. The API only lets you read them and observe their execution state.
- **Nightly execution at 3am CET/CEST.** Invoices are deduced from templates once a day; `nextExecutionDate`
  is when the next one will appear. There's no "run now" API.
- **You cannot list the invoices a template generated.** The docs state this explicitly. The link goes the
  other way: a generated *invoice* carries a reference back to its recurring template.
- **`finalize:true` recurring invoices are auto-emailed to the customer** on creation — unlike the invoices
  endpoint, where finalizing does not send. Surfacing/creating templates has a real-world side effect.
- **`executionStatus` has no error state.** A failed run keeps the template `ACTIVE`; you only learn of
  failure via `lastExecutionFailed` + `lastExecutionErrorMessage`. Don't infer health from status alone.
- **`startDate:null` ⇒ PAUSED, `nextExecutionDate:null` ⇒ paused/never-runs.** Watch nulls when forecasting.
- **Recurring-template collection is a reduced projection.** No `lineItems`/`taxAmounts`/`taxConditions`;
  `address` is just `{contactId,name}`. You must GET each template by id for full detail.
- **Recurring-template list has NO filters** — only `page`, `size`, `sort`. To find failed/paused/by-contact
  templates you must fetch every page and filter client-side. Sort keys: `createdDate`, `updatedDate`,
  `lastExecutionDate`, `nextExecutionDate` (default `updatedDate,DESC`).
- **Money is net *or* gross depending on `taxConditions.taxType`** (`net` vs `gross` leading), and articles
  carry both `netPrice`/`grossPrice` with a `leadingPrice` flag — the non-leading side is computed and
  read-only. Never sum a mix without normalizing which side is authoritative.
- **`taxRate` / `taxRatePercentage` are whole-number percents** (0/7/19), not fractions. `currency` is
  always `EUR` (only supported value).
- **Article create/update return an action-result, not the article** (`id`,`resourceUri`,`createdDate`,
  `updatedDate`,`version`). Re-GET to see the persisted entity. New resources start at `version:0`; PUT
  needs the current `version` (stale ⇒ 409).
- **Articles CAN be deleted** (204 / 404) — unlike contacts. But there's no reverse lookup to see whether
  an article is still referenced by vouchers before you delete it.
- **Profile sample ≠ profile property table.** Sample adds undocumented `features` and `subscriptionStatus`
  and omits `distanceSalesPrinciple`. Parse the profile leniently; don't hard-require documented fields.
- **`businessFeatures` gate capabilities.** Print-layouts, XRechnung, English/foreign invoices need
  `INVOICING_PRO`; regular bookkeeping needs `BOOKKEEPING`. Check the profile before assuming an endpoint works.
- **Countries and print-layouts return bare arrays** (no Pageable). Event-subscriptions list returns a
  `{content:[…]}` object but **without** paging metadata — it only looks Pageable.
- **Country `taxClassification` is the *current* country-level state** and can change as countries join/leave
  the EU. It is not a per-voucher determination — actual intra-community eligibility depends on org + contact.
- **Extended country codes exist** (`ES_CN`, `GR_69`, …). An invalid code makes voucher endpoints return the
  full list of supported codes in the error. Don't assume plain ISO alpha2 covers everything.
- **Files upload is multipart, not JSON**, and uses **legacy error handling** (different error body shape).
  202 (not 200/201). Content dedup by checksum returns the existing `id`/`voucherId` silently.
- **Uploaded voucher lifecycle:** immediately available at `vouchers/{id}` in status `blank`; after async OCR
  it becomes `unchecked` and only then does the `voucher.created` event fire. Don't treat 202 as "ready".
- **`GET /v1/files/{id}` is deprecated for sales vouchers** — use the per-voucher file subresource. Use
  `Accept: application/xml` to pull an e-invoice's XML (only when a separate XML exists; ZUGFeRD embeds XML
  in the PDF so only PDF is downloadable). Unsupported media types ⇒ 406; XML on non-XML voucher ⇒ 404.
- **Webhook create/get key mismatch:** POST returns `id`; GET returns `subscriptionId` (and no `version`).
- **Webhook callback carries no data — only `resourceId`.** You always have to GET the resource yourself.
  For `token.revoked`, `resourceId` is a `connectionId`, not a voucher; pre-store connection→refresh-token.
- **Subscriptions can't be updated — delete + recreate.** Duplicate (type+url) ⇒ 409. A HEAD request is
  sent to your `callbackUrl` at subscribe time to check SSL; bad cert ⇒ 406.
- **Revoking/regenerating the API key deletes ALL subscriptions.** They must be recreated after any key change.
- **Webhook delivery has aggressive auto-cleanup:** 404 or bad DNS ⇒ subscription auto-deleted (after retries);
  410 ⇒ removed immediately; 3xx followed at most 3×, never retried. Retry: 5×(10/20/40/80/160s), then after
  30 min, 20× every 2 h. Read timeout 5000 ms — ack fast (2xx: 200/201/202/204) and process async.

---

## What the API refuses to answer directly

These are derivations a user will ask for but that the reference/system endpoints cannot return — the
CLI must compute them. Prime "killer feature" material:

- **Monthly recurring revenue (MRR) / annual run-rate from recurring templates.** No aggregate endpoint —
  fetch all templates, normalize each `totalPrice` by its `executionInterval` (WEEKLY…ANNUALLY), and sum
  (respecting `executionStatus`, `startDate`/`endDate`, and null dates).
- **Forecast of upcoming recurring invoices ("what will bill next month / this quarter, and how much").**
  Must project from `nextExecutionDate` + `executionInterval` + `endDate` + `totalPrice` per template.
- **Which invoices came from which recurring template.** No template→invoices listing exists; you must scan
  invoices and match their back-reference to the template.
- **Health/failure roll-up of recurring templates** ("which subscriptions failed to bill, which are paused").
  No status filter; must page through everything and inspect `lastExecutionFailed` / `executionStatus`.
- **Filter recurring templates by contact / interval / status.** Not supported — client-side only.
- **Duplicate-article detection** (same GTIN or same articleNumber). The `articleNumber`/`gtin` filters only
  do exact single-value lookups; finding dupes means pulling the whole catalogue and grouping.
- **Unused / orphaned articles** ("which products are never referenced in a voucher"). No reverse index from
  article → vouchers; must cross-reference every voucher's line items.
- **A price list with both net and gross for a chosen tax scenario.** Each article stores one leading price;
  the other side is only computed at read time for the stored tax rate. Re-pricing for another rate is client-side.
- **Article catalogue value / count by type or tax rate.** No aggregation; page and tally.
- **"Is this address intra-community for VAT?" for a concrete voucher.** Countries only gives the current
  country-level `taxClassification`; the real per-voucher decision also depends on org + contact + `taxType`.
- **Webhook delivery history / audit** ("did event X get delivered, when, how many retries"). No delivery-log
  endpoint — reconciliation must happen in your own receiver.
- **Bulk / wildcard subscription management.** No "subscribe to everything"; each (eventType, callbackUrl) is
  its own subscription. Enumerating "am I subscribed to all events?" is client-side set math against the
  known event-type list.
- **Plan/quota/rate-limit budget.** The profile exposes capability flags (`businessFeatures`) but no numeric
  quota, remaining-request budget, or rate-limit headroom to plan against.

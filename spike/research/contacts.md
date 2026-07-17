# Contacts — Lexware Office API

Source: https://developers.lexware.io/docs/ (single static HTML page), section **"Contacts Endpoint"**.
All JSON below is copied **verbatim** from the official docs (real sample UUIDs, dates, enum values).
Base URL `https://api.lexware.io` (legacy `https://api.lexware.com` until Dec 2025). Auth header
`Authorization: Bearer <apiKey>`, `Accept: application/json`, `Content-Type: application/json`.

> Docs "Purpose" line says the endpoint "provides read access to contacts" — but create (POST) and
> update (PUT) are fully documented. There is **no DELETE** for contacts (you cannot delete a contact
> via the API; `archived` is read-only, so you cannot even archive/unarchive through the API).

---

## Endpoints

| METHOD | Path | Purpose | Notes / permissions |
|--------|------|---------|---------------------|
| POST   | `/v1/contacts` | Create a contact (company or person) | Body = contact JSON. `version` must be `0`. Returns an **action-result** (id + resourceUri + timestamps + version), **not** the full contact. Requires `Content-Type: application/json` (else 415). |
| GET    | `/v1/contacts/{id}` | Retrieve one contact by UUID | Returns the full contact object. Contains **no** createdDate/updatedDate. |
| PUT    | `/v1/contacts/{id}` | Update an existing contact | Must send the current `version` (optimistic locking → 409 on mismatch). Same required-field rules as create. Fails if any list field has >1 entry (see Gotchas). |
| GET    | `/v1/contacts?<filters>&page=<n>&size=<n>` | List / filter contacts (paginated) | Spring Pageable wrapper. Filters: `email`, `name`, `number`, `customer`, `vendor`. Multiple filters AND-combined. Fixed sort by `name ASC` — **contacts cannot be re-sorted**. |
| —      | `{appbaseurl}/permalink/contacts/view/{contactId}` | Deeplink (browser, not API) | View-only deeplink into the Lexware web app. There is **no** edit deeplink for contacts. |

There is no DELETE endpoint. There is no "count" / "aggregate" endpoint (but `totalElements` on a
filtered list gives you counts — see "What the API refuses to answer directly").

---

## Response examples

### GET a full company contact (roles customer + vendor) — "Contact Properties" sample

This is the docs' canonical full-object sample showing every optional block populated (company +
contactPersons + both address types + xRechnung + all email/phone buckets).

```json
{
  "id": "be9475f4-ef80-442b-8ab9-3ab8b1a2aeb9",
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "version": 1,
  "roles": {
    "customer": {
      "number": 10307
    },
    "vendor": {
      "number": 70303
    }
  },
  "company": {
    "name": "Testfirma",
    "taxNumber": "12345/12345",
    "vatRegistrationId": "DE123456789",
    "allowTaxFreeInvoices": true,
    "contactPersons": [
      {
        "salutation": "Herr",
        "firstName": "Max",
        "lastName": "Mustermann",
        "primary": true,
        "emailAddress": "contactpersonmail@lexware.de",
        "phoneNumber": "08000/11111"
      }
    ]
  },
  "addresses": {
    "billing": [
      {
        "supplement": "Rechnungsadressenzusatz",
        "street": "Hauptstr. 5",
        "zip": "12345",
        "city": "Musterort",
        "countryCode": "DE"
      }
    ],
    "shipping": [
      {
        "supplement": "Lieferadressenzusatz",
        "street": "Schulstr. 13",
        "zip": "76543",
        "city": "MUsterstadt",
        "countryCode": "DE"
      }
    ]
  },
  "xRechnung": {
    "buyerReference": "04011000-1234512345-35",
    "vendorNumberAtCustomer": "70123456"
  },
  "emailAddresses": {
    "business": [
      "business@lexware.de"
    ],
    "office": [
      "office@lexware.de"
    ],
    "private": [
      "private@lexware.de"
    ],
    "other": [
      "other@lexware.de"
    ]
  },
  "phoneNumbers": {
    "business": [
      "08000/1231"
    ],
    "office": [
      "08000/1232"
    ],
    "mobile": [
      "08000/1233"
    ],
    "private": [
      "08000/1234"
    ],
    "fax": [
      "08000/1235"
    ],
    "other": [
      "08000/1236"
    ]
  },
  "note": "Notizen",
  "archived": false
}
```

Note: this exact block is presented under "Contact Properties" as the shape of a contact; it is the
best reference for a company contact. Every field except `id`, `organizationId`, `version`,
`roles`, and (`company` xor `person`) is optional. The `"MUsterstadt"` casing typo is in the
original docs — quoted verbatim.

### GET a private-person contact — "Person Details" sample

```json
{
  "id": "e9066f04-8cc7-4616-93f8-ac9ecc8479c8",
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "version": 0,
  "roles": {
    "customer": {
      "number": 10308
    }
  },
  "person": {
    "salutation": "Frau",
    "firstName": "Inge",
    "lastName": "Musterfrau"
  },
  "archived": false
}
```

Note: a person contact carries a `person` object (never `company`). The `person` object supports only
`salutation`, `firstName`, `lastName` — no per-person addresses/emails/phones inside it (those live
in the top-level `addresses` / `emailAddresses` / `phoneNumbers` blocks).

### POST /v1/contacts — create request (create a customer of type person)

```
curl https://api.lexware.io/v1/contacts
  -X POST
  -H "Authorization: Bearer {accessToken}"
  -H "Content-Type: application/json"
  -H "Accept: application/json"
  -d '
{
  "version": 0,
  "roles": {
    "customer": {
    }
  },
  "person": {
    "salutation": "Frau",
    "firstName": "Inge",
    "lastName": "Musterfrau"
  },
  "note": "Notizen"
}'
```

Note: the role is sent as an **empty object** `"customer": {}` — you do **not** (and cannot) set the
customer/vendor `number`; Lexware assigns it. `version` must be `0` on create.

### POST /v1/contacts — create response (action-result, NOT the full contact)

```json
{
  "id": "66196c43-baf3-4335-bfee-d610367059db",
  "resourceUri": "https://api.lexware.io/v1/contacts/66196c43-bfee-baf3-4335-d610367059db",
  "createdDate": "2023-06-29T15:15:09.447+02:00",
  "updatedDate": "2023-06-29T15:15:09.447+02:00",
  "version": 1
}
```

Note: the response is a small **action-result** — it returns the new `id`, a `resourceUri`, both
timestamps, and the incremented `version` (now `1`). To read the full contact (and to learn the
assigned customer/vendor `number`), you must follow up with `GET /v1/contacts/{id}`.
**Docs quirk (verbatim):** the `id` (`66196c43-baf3-4335-bfee-...`) and the UUID inside `resourceUri`
(`66196c43-bfee-baf3-4335-...`) differ — the 2nd/3rd UUID segments are transposed. This is an error
in the docs' sample; in real responses `id` and the resourceUri tail are the same value.

### GET /v1/contacts/{id} — retrieve response

```json
{
  "id": "e9066f04-8cc7-4616-93f8-ac9ecc8479c8",
  "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
  "version": 0,
  "roles": {
    "customer": {
      "number": 10308
    }
  },
  "person": {
    "salutation": "Frau",
    "firstName": "Inge",
    "lastName": "Musterfrau"
  },
  "note": "Notizen",
  "archived": false
}
```

Note: the retrieve response has **no** `createdDate`/`updatedDate` — the contact resource does not
expose timestamps on read (only the create/update action-result does). `roles.customer.number`
(10308) is present because Lexware assigned it after creation.

### GET /v1/contacts?page=0 — paginated list response (Spring Pageable wrapper)

```json
{
  "content": [
    {
      "id": "e9066f04-8cc7-4616-93f8-ac9ecc8479c8",
      "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
      "version": 0,
      "roles": {
        "customer": {
          "number": 10308
        }
      },
      "person": {
        "salutation": "Frau",
        "firstName": "Inge",
        "lastName": "Musterfrau"
      },
      "archived": false
    },
    {
      "id": "313ef116-a432-4823-9dfe-1b1200eb458a",
      "organizationId": "aa93e8a8-2aa3-470b-b914-caad8a255dd8",
      "version": 0,
      "roles": {
        "customer": {
          "number": 10309
        }
      },
      "person": {
        "salutation": "Herr",
        "firstName": "Max",
        "lastName": "Mustermann"
      },
      "archived": true
    }
  ],
  "totalPages": 1,
  "totalElements": 2,
  "last": true,
  "sort": [
    {
      "direction": "ASC",
      "property": "name",
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

Note: page items are the same contact shape as a single GET. Default `size` is 25 (max 250 for
contacts). Sort is fixed to `name ASC`. Note the second item has `"archived": true` — **archived
contacts are returned in the default list** (there is no filter to exclude them).

### Filter request examples (verbatim)

```
curl https://api.lexware.io/v1/contacts?email=max@gmx.de&name=Mustermann
  -X GET
  -H "Authorization: Bearer {accessToken}"
  -H "Accept: application/json"
```

```
curl https://api.lexware.io/v1/contacts?vendor=true&customer=false
  -X GET
  -H "Authorization: Bearer {accessToken}"
  -H "Accept: application/json"
```

Note: multiple filters are AND-combined. Filter values must be URL-encoded. `vendor=true&customer=false`
means "has the vendor role AND does not have the customer role".

---

## Key fields

| Field | Type | Meaning |
|-------|------|---------|
| `id` | uuid (string) | Contact UUID, assigned by Lexware on creation. Read-only. |
| `organizationId` | uuid (string) | The Lexware organization the contact belongs to. Read-only. |
| `version` | integer | Optimistic-locking revision. Increments on each change. Send `0` on POST; echo the last-read value on PUT. |
| `roles` | object | Which roles the contact has. Presence of a sub-object = has that role. **At least one role is required.** |
| `roles.customer` | object | Present ⇒ contact is a customer. On create send `{}`. |
| `roles.customer.number` | integer | Unique customer number in the org, **assigned by Lexware**. Cannot be set or changed. Read-only. |
| `roles.vendor` | object | Present ⇒ contact is a vendor. On create send `{}`. |
| `roles.vendor.number` | integer | Unique vendor number in the org, assigned by Lexware. Read-only. |
| `company` | object | Present ⇒ company-type contact. **Mutually exclusive with `person`.** |
| `company.name` | string | Company name. Required (non-empty) for company contacts. |
| `company.taxNumber` | string | "Steuernummer" (German tax number), e.g. `"12345/12345"`. |
| `company.vatRegistrationId` | string | "Umsatzsteuer-ID" / VAT ID; must follow German VAT-ID rules, e.g. `"DE123456789"`. |
| `company.allowTaxFreeInvoices` | boolean | `true`/`false` — allow tax-free invoices for this company. |
| `company.contactPersons` | list<object> | Contact persons at the company. On create/update **max 1 entry** allowed. |
| `company.contactPersons[].salutation` | string | Max 25 chars. Optional (changed to optional per changelog). |
| `company.contactPersons[].firstName` | string | Contact person's first name. |
| `company.contactPersons[].lastName` | string | Required (non-empty) for company contacts. |
| `company.contactPersons[].primary` | boolean | Primary contact person shown on vouchers. Default `false`. |
| `company.contactPersons[].emailAddress` | string | Contact person's email (single string, not a list). |
| `company.contactPersons[].phoneNumber` | string | Contact person's phone (single string). |
| `person` | object | Present ⇒ private-person contact. **Mutually exclusive with `company`.** |
| `person.salutation` | string | Max 25 chars. Optional. |
| `person.firstName` | string | Person's first name. |
| `person.lastName` | string | Required (non-empty) for person contacts. |
| `addresses.billing` | list<address> | Billing addresses. On create/update **max 1**. |
| `addresses.shipping` | list<address> | Shipping addresses. On create/update **max 1**. |
| address `.supplement` | string | Additional address line. |
| address `.street` | string | Street + house number. |
| address `.zip` | string | Postal code (string, not int). |
| address `.city` | string | City. |
| address `.countryCode` | string | ISO 3166 alpha-2, e.g. `"DE"`. **Required** when an address is present. |
| `xRechnung.buyerReference` | string | Customer's Leitweg-ID for the German XRechnung system, e.g. `"04011000-1234512345-35"`. |
| `xRechnung.vendorNumberAtCustomer` | string | Your vendor number as used by that customer. If `buyerReference` is set, this **must** be set too. |
| `emailAddresses.{business,office,private,other}` | list<string> | Email buckets by type. On create/update **max 1 per bucket**. |
| `phoneNumbers.{business,office,mobile,private,fax,other}` | list<string> | Phone buckets by type. On create/update **max 1 per bucket**. |
| `note` | string | Free note, max 1000 chars. Informational only. |
| `archived` | boolean | Whether the contact is archived. **Read-only.** |
| (action-result) `resourceUri` | string | Full URL of the created resource (POST/PUT response only). |
| (action-result) `createdDate` / `updatedDate` | string | ISO 8601 with offset, e.g. `"2023-06-29T15:15:09.447+02:00"`. **Only in the POST/PUT action-result, not in the contact object itself.** |

Enum-like value sets:
- `salutation`: free string (docs samples use German `"Herr"`, `"Frau"`), max 25 chars — not a
  closed enum in the API.
- `sort.direction` / `nullHandling` in the page wrapper: `"ASC"`/`"DESC"`, `"NATIVE"` (fixed;
  contacts always sort `name ASC`).
- `roles` keys: `customer`, `vendor` (a contact can be one or both, never zero).
- email buckets: `business`, `office`, `private`, `other`.
- phone buckets: `business`, `office`, `mobile`, `private`, `fax`, `other`.

---

## Gotchas

- **`company` xor `person` — never both.** Each contact is exactly one type. If `company` is present,
  `person` must be absent, and vice-versa. Exactly one of them is required.
- **At least one role required.** You must send `roles.customer` and/or `roles.vendor` (as `{}` on
  create). A contact with no roles is rejected.
- **Role numbers are read-only and Lexware-assigned.** `customer.number` / `vendor.number` cannot be
  set on create or changed on update. They only appear *after* creation (fetch via GET). On create
  you send the role as an empty object `{}`.
- **Create returns an action-result, not the contact.** POST → `{id, resourceUri, createdDate,
  updatedDate, version}` only. You must GET the id to see the full contact and the assigned number.
- **No timestamps on the contact object.** GET (single or list) never returns `createdDate`/
  `updatedDate`. They exist only in the POST/PUT action-result. You cannot ask the API "when was this
  contact created/last changed" after the fact.
- **Docs sample UUID mismatch.** In the create-response sample, `id` and the UUID in `resourceUri`
  differ (segments transposed). It's a docs typo; in reality they match.
- **Max ONE entry per list on write.** `addresses.billing`, `addresses.shipping`, each
  `emailAddresses.*` bucket, each `phoneNumbers.*` bucket, and `company.contactPersons` may hold at
  most **one** entry when creating or updating. GET can *return* more (data entered via the web app),
  but any PUT on such a contact fails with a validation error (406). A CLI editing a contact must
  guard against multi-entry lists it can't round-trip.
- **`archived` is read-only.** You cannot archive/unarchive/delete a contact via the API. There is no
  DELETE endpoint at all. Archived contacts still appear in the default list.
- **No filter to exclude archived contacts.** The default list mixes active and archived
  (`archived: true` items appear). Filtering active-only must be done client-side.
- **Contacts cannot be sorted.** Sort is hard-wired to `name ASC`; the `sort` query param is ignored
  for contacts. "Newest contact" / "recently changed" is not answerable by sorting — you'd have to
  page the entire list (and even then there are no timestamps to sort by).
- **Only 5 filters exist:** `email`, `name`, `number`, `customer`, `vendor`. You cannot filter by
  city, country, VAT-ID, tax number, `allowTaxFreeInvoices`, xRechnung readiness, note text, or
  archived status. Anything else = fetch-all + client-side filter.
- **`email`/`name` filters need ≥3 chars** and are **case-insensitive substring** matches. `email`
  also matches emails inside `company.contactPersons`.
- **`_` and `%` are wildcards in `email`/`name` filters.** `_` = any single char, `%` = any run of
  chars. So `email=n_d_e@example.com` also matches `john.doe@example.com`. To match a literal `_`
  or `%`, escape with a backslash (`a\_b@example.com`). A CLI doing exact lookups must escape user
  input or it will get false positives.
- **`number` filter matches customer OR vendor number.** `number` is an integer; it returns contacts
  whose customer *or* vendor number equals it. It does not distinguish the two.
- **URL-encode all filter values.** Especially `email` (the `@`, `+`, wildcards) and `name`.
- **Pagination:** Spring Pageable wrapper `{content, totalPages, totalElements, last, sort, size,
  number, first, numberOfElements}`. `page` is zero-indexed. Default `size` 25, **max 250** for
  contacts. `totalElements` capped at 10,000; exceeding the window yields "Maximum search window size
  exceeded" (narrow the query).
- **Optimistic locking:** PUT must carry the current `version`. Stale version → **409 Conflict**.
  Initial POST uses `version: 0`. Invalid data on POST/PUT → **406 Not Acceptable**. Missing
  `Content-Type: application/json` → **415**.
- **Rate limit 2 req/s (token bucket), org-wide across all endpoints.** Over the limit → **429 Too
  Many Requests** (request not performed). Use a client-side token bucket / backoff; the auth server
  has its own separate undocumented limit. This matters a lot when paging thousands of contacts.
- **Money/tax fields are metadata only.** `allowTaxFreeInvoices`, `vatRegistrationId`, `taxNumber`
  live on the contact but there are no balances/amounts on a contact — all monetary reality lives on
  invoices/vouchers keyed by contact id.
- **Deeplink is view-only and not an API call.** `{appbaseurl}/permalink/contacts/view/{contactId}`
  opens the web app; there's no edit deeplink for contacts.

---

## What the API refuses to answer directly

The contact resource is pure master data — no financial or relationship aggregates. These are the
questions a user will ask that the CLI must compute itself (usually by joining contacts to the
invoices / vouchers / quotations endpoints, or by scanning the full contact list):

- **Total open receivables per customer / overall.** Not on the contact. Must sum open invoice
  amounts from the invoices/voucherlist endpoints filtered by `contactId`.
- **Overdue / aging buckets (0-30, 31-60, 60+ days) for a customer.** Must derive from invoice due
  dates + open amounts elsewhere; nothing here.
- **Revenue / turnover per customer for a period.** Must aggregate finalized invoices/vouchers by
  contact id and date range; the contact carries no totals.
- **Duplicate-contact detection / merge.** No dedupe or merge endpoint. Must page the whole list and
  fuzzy-compare names / emails / VAT-IDs / addresses client-side. (And the `_`/`%` wildcard behavior
  of the `email` filter makes naive "search by email" unreliable for exactness.)
- **"How many customers vs vendors do I have?"** Partly answerable via `totalElements`:
  `GET /v1/contacts?customer=true&size=1` → `totalElements`; same with `vendor=true`. But a
  role/segment breakdown beyond those two booleans is not.
- **Which contacts are XRechnung-ready** (have `buyerReference` set)? No filter — must scan all and
  inspect `xRechnung`.
- **Filter/segment by city, country, VAT-ID, tax number, `allowTaxFreeInvoices`, note text, or
  archived status.** None are filterable — fetch-all + client-side filter.
- **"Most recently created / recently modified contacts."** No timestamp on the contact object and no
  sort by date; contacts sort only by `name ASC`. Not answerable via the API — you'd need to capture
  createdDate from action-results yourself at write time.
- **Look up a contact by exact email or exact name.** Only substring + wildcard matching (min 3
  chars); exact-match must be enforced client-side after fetching candidates.
- **Enumerate all contact persons across the org, or find "which contact has person X".** No such
  query; the `email` filter does reach into contactPersons emails, but there's no contact-person
  listing.
- **Next customer/vendor number, or number ranges.** Numbers are Lexware-assigned and read-only;
  the API won't tell you the next number or let you query by range (only exact `number`).
- **Count of contacts linked to open documents, or a contact's document history.** The contact has no
  back-references to invoices/quotations; must be joined from those endpoints.
- **Quote→invoice conversion or any document creation** is not part of contacts (lives on the
  quotations/invoices endpoints); a contact only provides the addressee data.

# Conventions & System — Lexware Office API

> Cross-cutting conventions that every endpoint of the Lexware Office (formerly *lexoffice*)
> public REST API shares: the base URL, auth, `/v1` URI layout, the `Pageable` pagination
> wrapper, optimistic locking (`version`), rate limiting (HTTP 429), the two error-envelope
> shapes, HTTP status-code semantics, date/money formats, and how filtering/search works.
> Source: the single static Slate HTML page at <https://developers.lexware.io/docs/>
> (captured 2026-07-18). All JSON below is quoted **verbatim** from that page.

---

## Base facts (confirmed against the docs)

| Fact | Value | Source note |
|------|-------|-------------|
| Base URL (current) | `https://api.lexware.io` | "endpoints are exposed by a gateway located at https://api.lexware.io" |
| Gateway migration | Domain changed **26 May 2025** as part of the lexoffice→Lexware rebrand. | Introduction banner |
| Legacy gateway | "the previously used API Gateway URL available **until December 2025**" — the docs do **not** print the old hostname. The historical lexoffice gateway was `https://api.lexoffice.io`. **The base-fact `https://api.lexware.com` is NOT confirmed anywhere in the docs** (0 hits for `lexware.com`/`lexoffice.io`). Treat `api.lexware.io` as the only documented host. | grep of full page |
| Auth header | `Authorization: Bearer {accessToken}` (access token == API key, used interchangeably) | 56 `Bearer` occurrences, all examples |
| API key generation | <https://app.lexware.de/addons/public-api> | Introduction |
| Content-Type / Accept | `application/json` (JSON only). File uploads use `multipart/form-data`. | HTTP 415 description + files endpoint |
| Versioning | `/v1` path prefix; "changed only if breaking changes are required" | URI Components |
| Rate limit | **2 requests/second**, token-bucket, all endpoints share the budget → HTTP 429 | API Rate Limits |
| Pagination | Spring "Pageable" wrapper (see below) | Paging of Resources |
| Optimistic locking | numeric `version` on versioned resources; wrong version on PUT → 409 | Optimistic Locking |
| Request timeout | 30 seconds (gateway) → 504 if exceeded; request may still have succeeded | HTTP 504 description |

URI pattern: `https://{hostname}/{version}/{resourceUri}{?query}` e.g. `https://api.lexware.io/v1/contacts?page=0`.

---

## Endpoints

There are **no endpoints dedicated to "conventions"** — these rules are cross-cutting. The
representative request patterns that *demonstrate* the conventions (and that the CLI will
reuse everywhere) are:

| METHOD | Path pattern | Purpose | Notes |
|--------|--------------|---------|-------|
| GET | `/v1/{collection}?page=0&size=25&sort=…` | Paged list retrieval (Pageable wrapper) | `page` zero-indexed; default `size` 25, max 100 or 250 per endpoint; `totalElements` capped at 10 000 |
| GET | `/v1/{collection}?filter_1=v1&…&filter_n=vn` | Filtered list retrieval | Multiple filters AND-combined; a filter must not appear twice; unset filters ignored |
| GET | `/v1/contacts?email=…&name=…&number=…&customer=…&vendor=…` | Concrete filter example (contacts) | `email`/`name` need ≥3 chars, case-insensitive substring, support `_`/`%` wildcards |
| GET | `/v1/articles?articleNumber=…&gtin=…&type=PRODUCT|SERVICE` | Concrete filter example (articles) | exact-match filters |
| PUT | `/v1/{collection}/{id}` (body carries current `version`) | Update with optimistic-lock check | wrong/stale `version` → 409 Conflict |
| POST | `/v1/{collection}` (body `version: 0` for versioned resources) | Create | initial `version` must be `0` |

---

## Response examples

### 1. Pagination — `Pageable` wrapper (canonical, empty content)

`GET https://api.lexware.io/v1/contacts?page=0`

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

Note: `content` is shown truncated (`...`) in the docs; every other wrapper field is
verbatim. This is the authoritative field set of the Pageable envelope.

### 2. Pagination — real populated page (contacts list)

`GET https://api.lexware.io/v1/contacts?page=0`

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

Note: fully verbatim, including real-looking UUIDs. Confirms `version` and `organizationId`
appear on every entity, and that wrapper key ordering is **not** stable (here `totalPages`
comes before `last`, unlike example 1 — do not depend on key order).

### 3. Pagination — populated page with money & enums (articles list)

`GET https://api.lexware.io/v1/articles?page=0`

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

Note: money is a bare JSON number (`61.90`, `73.66`), no minor-units/cents integer, no
currency symbol on `price`; `leadingPrice` enum is `NET`/`GROSS`; `taxRate` is a plain
integer percentage.

### 4. Money shape inside vouchers (unitPrice / totalPrice / taxAmounts)

Fragment quoted verbatim from invoice/voucher sample bodies (currency-tagged money used by
all sales-voucher endpoints):

```json
"unitPrice": { "currency": "EUR", "netAmount": 13.4, "grossAmount": 15.946, "taxRatePercentage": 19 }
```
```json
"totalPrice": { "currency": "EUR", "totalNetAmount": 31.8, "totalGrossAmount": 36.89, "totalTaxAmount": 5.09 }
```
```json
"taxAmounts": [ { "taxRatePercentage": 0, "taxAmount": 0, "netAmount": 5 }, { "taxRatePercentage": 19, "taxAmount": 5.09, "netAmount": 26.8 } ]
```

Note: sales vouchers use a **currency-tagged** money object (`currency`+`*Amount`), whereas
the `articles` endpoint uses the **currency-less** `price` object (`netPrice`/`grossPrice`).
Two different money shapes coexist across the API.

### 5. Error envelope — "Regular" error response (used by most endpoints)

HTTP 406, `POST /v1/invoices` with a missing required field:

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

Note: verbatim. `details[].message` is **German** ("darf nicht leer sein" = "must not be
empty") — messages are localized and explicitly "not suitable for presenting to end-users".
Used by all endpoints EXCEPT `contacts`, `files`, `vouchers` (see next). Examples the docs
name: `event-subscriptions`, `invoices`, `order-confirmations`, `profile`, `voucherlist`.

### 6. Error envelope — "Legacy" error response (contacts, files, vouchers only)

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

Note: verbatim. Completely different shape — a top-level `IssueList` array. Used ONLY by
`contacts`, `files`, `vouchers`. A CLI must branch its error parser on the endpoint (or on
"does the body have `IssueList` vs `details`").

### 7. Error envelope — Authorization / Connection errors (gateway-level)

These bodies are gateway/auth-layer, shaped `{ "message": ... }` (neither of the two schemas above):

```json
{ "message": "Unauthorized" }
```
(HTTP 401 — no token, malformed token, invalid token, or client disabled)

```json
{"message": "'{accessToken}' not a valid key=value pair (missing equal-sign) in Authorization header: 'Bearer {accessToken}'."}
```
(HTTP 403 — resource not available; possibly wrong URL or method)

```json
{ "message": "Internal server error or rate limit exceeded" }
```
(HTTP 500 — server unavailable, internal problem, **or rate limit exceeded**)

```json
{ "message": "Endpoint request timed out" }
```
(HTTP 504 — 30-second timeout; request may still have been processed)

Note: 503 has no fixed body ("Detail information. May be null."). So the CLI must handle up
to **three** distinct error shapes: `{message}`, `{IssueList:[…]}`, and the regular
`{timestamp,status,error,path,traceId,message,details}`.

---

## Key fields

### Pageable wrapper

| Field | Type | Meaning |
|-------|------|---------|
| `content` | array | The page's entities (endpoint-specific shape). |
| `first` | boolean | Whether this is the first page. |
| `last` | boolean | Whether this is the last page. |
| `totalPages` | integer | Total pages matching the query. |
| `totalElements` | integer | Total matching elements, **capped at 10 000**. |
| `numberOfElements` | integer | Count of elements on the current page. |
| `size` | integer | Page size of the current page. |
| `number` | integer | Current page index, **zero-based**. |
| `sort` | array | Sort descriptors: `{direction, property, ignoreCase, nullHandling, ascending}`. |

Paging query params: `page` (integer, 0-indexed), `size` (integer, default 25, max
100/250 per endpoint), `sort` (string, endpoint-defined — some resources like contacts
cannot be re-sorted).

Max page size per endpoint (from the docs table): `articles` 250, `contacts` 250,
`recurring-templates` 250, `voucherlist` 250, `vouchers` 250. (Default max is 100 where not
listed.)

### Regular error object

| Field | Type | Meaning |
|-------|------|---------|
| `timestamp` | dateTime (RFC 3339) | When the error occurred. |
| `status` | number | HTTP status code (e.g. 406). |
| `error` | string | Short description of the status ("Not Acceptable"). |
| `path` | string | The called endpoint path. |
| `traceId` | string | ID to trace the error in Lexware logs (quote it in support tickets). |
| `message` | string | Human-readable, **localized (German)**, not end-user-safe. |
| `details` | array (optional) | Validation issues: `violation` (e.g. `NOTNULL`), `field` (dotted/indexed path like `lineItems[0].unitPrice.taxRatePercentage`), `message` (localized). |

### Legacy error object (`IssueList[]`)

| Field | Type | Meaning |
|-------|------|---------|
| `i18nKey` | string | Machine-ish error code (e.g. `missing_entity`, `bad_request_error`, `technical_error`). |
| `source` | string \| null | Offending field/attribute (e.g. `company.name`). |
| `type` | string | Category (e.g. `validation_failure`, `bad_request_error`, `technical_error`). |
| `additionalData` | any \| null | Extra detail; often null. |
| `args` | any \| null | e.g. valid range or locale code; often null. |

Documented legacy `i18nKey` values: `missing_entity` (406, value null/empty),
`bad_request_error` (400, generic incl. filter size out of range), `technical_error` (500,
structural contact failures like `contact_is_neither_customer_nor_vendor`).

### Money (two shapes)

| Field | Type | Meaning |
|-------|------|---------|
| `price.netPrice` / `price.grossPrice` | number | Articles: net/gross unit price, no currency field. |
| `price.leadingPrice` | enum `NET`\|`GROSS` | Which of net/gross is authoritative. |
| `price.taxRate` | integer | VAT percentage (article). |
| `unitPrice.currency` | string ISO-4217 (`EUR`) | Voucher money is currency-tagged. |
| `unitPrice.netAmount` / `grossAmount` | number | Up to **4 decimals**. |
| `unitPrice.taxRatePercentage` | number | VAT percentage on a line item. |
| `totalPrice.totalNetAmount` / `totalGrossAmount` / `totalTaxAmount` | number | Up to **2 decimals**, read-only (server-computed). |

Precision rules (verbatim from field docs): `quantity`, `unitPrice.netAmount`,
`unitPrice.grossAmount` → **up to 4 decimals**; all `total*Amount`, `taxAmount`, line-item
`discountPercentage`, `netAmount`/`grossAmount` at total level → **up to 2 decimals**.

### Common entity fields

| Field | Type | Meaning |
|-------|------|---------|
| `id` | UUID string | Resource id (e.g. `e9066f04-8cc7-4616-93f8-ac9ecc8479c8`). |
| `organizationId` | UUID string | Owning organization (see FAQ "Find out your organization id"). |
| `version` | integer | Optimistic-lock revision; `0` on create, echo current value on PUT. |
| `archived` | boolean | Soft-archive flag (contacts). |

---

## Gotchas

- **No rate-limit headers.** The page documents 429 but shows **no** `X-RateLimit-*`,
  `Retry-After`, or quota headers (0 hits). The client cannot read remaining budget — it
  must self-throttle to ≤2 req/s (token bucket / sleep) and treat 429 as retry-with-backoff.
  Jitter across the network means enforcing exactly 2/s with no buffer will still get you
  rate-limited; leave headroom.
- **429 can masquerade as 500.** The gateway 500 body literally says *"Internal server error
  **or rate limit exceeded**"*. A 500 with that message may actually be throttling — back off,
  don't just fail.
- **The auth server has separate, undocumented rate limits.** Overrunning it blocks the
  client for seconds→minutes, and *permanently* if you keep hammering. OAuth/token calls need
  their own throttle.
- **Two (really three) error envelopes.** `contacts`, `files`, `vouchers` return the legacy
  `{IssueList:[…]}`; everything else returns `{timestamp,status,error,path,traceId,message,details}`;
  gateway/auth errors return `{message}`. A single error parser must handle all three.
- **Error messages are German and not stable.** `details[].message` = "darf nicht leer sein".
  Branch on `violation`/`i18nKey` codes, never on the human message string.
- **`totalElements` is capped at 10 000.** Beyond that you get `Maximum search window size
  exceeded`. You cannot page past ~10k results nor trust `totalElements` as an exact count of
  large sets — you must narrow date/other filters. This kills naive "count all X" logic.
- **Pagination is zero-indexed** (`page=0` is the first page) and **wrapper key order is not
  stable** across responses — parse by key, never by position.
- **Not everything is sortable.** Some resources (e.g. contacts) have a fixed predefined sort
  and ignore `sort`. Default page size is 25; you must raise `size` (max 100/250) to avoid
  excessive round trips at 2 req/s.
- **Optimistic locking forces read-before-write.** Every PUT needs the *current* `version`;
  a stale value → 409 Conflict (or 406 in some validation paths). You cannot blind-update — a
  GET must precede each PUT, doubling request cost. Create (POST) must send `version: 0`.
- **Money has two incompatible shapes** (articles `price.netPrice`/`grossPrice`/`leadingPrice`
  vs voucher `unitPrice.currency`/`netAmount`/`grossAmount`). Different precision too (unit
  amounts 4 decimals, totals 2 decimals). Do arithmetic in decimal, not float, and round to
  the documented precision.
- **`leadingPrice` / gross-vs-net matters.** Whether net or gross is authoritative is a field,
  not an assumption; totals are server-computed and read-only — don't send them.
- **Dates are strict RFC 3339 / ISO 8601:** pattern `yyyy-MM-ddTHH:mm:ss.SSSXXX` — literal
  `T`, **exactly 3** millisecond digits, timezone `Z` or offset `+00:00` (with the colon).
  Anything else → 406. Example: `2022-04-27T09:30:00.000+02:00`. No bare dates, no 2-digit ms.
- **Search strings need double encoding.** For contacts/vouchers/voucherlist search, `&`,`<`,`>`
  must be **HTML-encoded first** (`&amp;`,`&lt;`,`&gt;`) *and then* URL-encoded. "johnson &
  partner" → `name=johnson%20%26amp%3B%20partner`. Using plain URL encoding gives wrong
  results; other endpoints must NOT use this double encoding.
- **Filter wildcards `_` and `%` are active in `email`/`name` contact filters.** `_` = any
  single char, `%` = any run of chars; matching is case-insensitive substring. `email=n_d_e@…`
  unexpectedly matches `john.doe@…`. Escape literals with backslash (`a\_b`). `email`/`name`
  need ≥3 chars.
- **Multiple filters are AND-only, and a filter may not repeat.** No OR, no ranges within a
  single param. Unset filters are ignored.
- **Country codes are ISO 3166 alpha-2 plus tax-region extensions** like `ES_CN` (Canary
  Islands), `GR_69` (Mount Athos). An invalid code makes endpoints (e.g. invoices) return the
  full supported list; or query the `countries` endpoint.
- **30-second gateway timeout → 504, but the request may have succeeded.** For non-idempotent
  POSTs, a 504 is ambiguous; verify before retrying to avoid duplicates.
- **Collective contact concept.** A generic customer/vendor stand-in to book against without
  creating a real contact per order — relevant when the CLI resolves contact references.

---

## What the API refuses to answer directly

These are aggregations/derivations a user will want but the API forces the client to compute
(each one is a candidate "killer feature" for the CLI):

- **Exact totals for large sets.** `totalElements` caps at 10 000 and errors past a 10k search
  window — "how many vouchers/contacts do I have" is unanswerable for big accounts without
  slicing by date/filter and summing client-side.
- **Any cross-collection or account-wide aggregate.** No total open receivables, no overdue
  buckets (0-30/30-60/60-90), no revenue-for-a-period, no tax/VAT summary across vouchers.
  Pagination is per-endpoint; there is no query/aggregation layer — the client must page every
  voucher and sum `totalPrice`/`taxAmounts` itself (respecting 2 req/s → slow).
- **Remaining rate-limit budget.** No header tells you how many requests you have left; the CLI
  must model the token bucket locally to schedule work.
- **Duplicate detection.** No "find duplicate contacts" — must be computed by pulling contacts
  and comparing names/emails (and the wildcard/HTML-encoding search quirks make even that
  fragile).
- **"What changed since X".** Most collections have no delta/`updatedSince` filter (only
  event-subscriptions webhooks and voucherlist date filters exist). Incremental sync must be
  built from event subscriptions or brute-force re-paging.
- **Safe blind updates.** You cannot PUT without first GETting the current `version`; the API
  refuses to just "set field Y" — the CLI should encapsulate the read-modify-write + 409 retry.
- **Bulk operations.** No batch create/update/delete endpoint. N resources = N requests at
  ≤2/s, so the CLI's value is smart batching, throttling, resumability, and progress reporting.
- **OR / range filtering.** Filters are AND-only and single-valued, so "customers matching A or
  B" or numeric ranges must be assembled from multiple calls and merged client-side.

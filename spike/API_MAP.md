# Lexware Office API — the map (synthesis)

Assembled 2026-07-18 from a 6-agent pass over the official docs
(developers.lexware.io — one static page, no OpenAPI spec). The **detail lives in
`research/<area>.md`** (4,139 lines, 66 verbatim JSON examples); this file is the
navigation and the cross-cutting truth. `../BUILDING.md` is the build playbook.

> **No test instance exists for Lexware Office.** The verbatim JSON in
> `research/*.md` and `RESPONSE_EXAMPLES.md` is therefore the fixture corpus the
> hermetic tests run against. Trust it over memory; confirm against a live key
> once if one is granted (the docs have had transcription typos — see below).

---

## 1. Cross-cutting conventions (from `research/conventions.md`)

| thing | truth |
|---|---|
| Base URL | `https://api.lexware.io` (since the 26 May 2025 rebrand). Legacy gateway until Dec 2025; its hostname is **not** printed in the docs — the "api.lexware.com" base-fact was NOT confirmed (0 hits). |
| Version | `/v1/` path prefix on every resource. |
| Auth | `Authorization: Bearer <apiKey>`. Key from `https://app.lexware.de/addons/public-api`. Single key, no OAuth for the public API. |
| Content | `application/json` (except file up/download). |
| **Rate limit** | **2 req/sec, org-wide across ALL endpoints → 429.** No `X-RateLimit-*` or `Retry-After` headers exist — the client must **model a local token bucket and self-throttle**; jitter means even exactly-2/s gets throttled, so aim slightly under. |
| **429 disguise** | **A 429 can arrive as HTTP 500** whose body literally reads `"Internal server error or rate limit exceeded"`. The retry logic must treat that specific 500 as a rate-limit, not a hard error. |
| **Error envelopes** | **THREE incompatible shapes.** (1) legacy `{"IssueList":[...]}` for **contacts / files / vouchers only**; (2) regular `{timestamp,status,error,path,traceId,message,details:[...]}` for everything else; (3) gateway `{"message":...}` for auth/connection errors. The client's error mapper must handle all three. |
| Error messages | **Localized German and unstable** (`"darf nicht leer sein"`). Branch on `violation`/`i18nKey`/status codes, **never** on the message string. |
| Validation status | Bad data → **406 Not Acceptable** (not 400). Missing `Content-Type` → **415**. Stale `version` → **409 Conflict**. |
| Pagination | Spring **"Pageable"** wrapper: `{content:[...], totalPages, totalElements, size, number, first, last, numberOfElements, sort:[...]}`. **Zero-indexed** (`page=0` is first). **Key order is NOT stable** — parse by key, never position. |
| Pagination cap | **`totalElements` caps at 10,000**; paging past a ~10k window errors (`"Maximum search window size exceeded"`). Large sets must be sliced by date/filter and summed client-side. |
| **Stop rule** | Has an authoritative `totalPages`/`last` → **page until `last==true`** (OpenProject's rule). This is the OPPOSITE of drone's "short page = done" — copying drone truncates. |
| Optimistic locking | Numeric `version` on every mutable resource. **POST create sends `version: 0`; PUT must echo the current version or 409.** No blind updates — always read-before-write. |
| Money | **TWO incompatible shapes.** Articles: `price{netPrice,grossPrice,leadingPrice(NET\|GROSS),taxRate}` (no currency). Vouchers/documents: `unitPrice{currency,netAmount,grossAmount,taxRatePercentage}`. **Unit amounts allow 4 decimals; totals are 2dp and server-computed/read-only.** Never float — decimals, carried exactly, in a pure `money.py`. |
| Dates | Strict RFC3339 `yyyy-MM-ddTHH:mm:ss.SSSXXX` — literal `T`, **exactly 3 millisecond digits**, tz `Z` or `+00:00` with colon. Anything else → 406. |
| Search encoding | Contacts/vouchers/voucherlist filters must be **HTML-encoded THEN URL-encoded (double)**. Other endpoints must NOT. Contact `email`/`name` filters silently apply SQL wildcards `_` (one char) and `%` (any run), need ≥3 chars, case-insensitive substring — **escape with backslash for exact lookups**, or `n_d_e@x` also matches `john.doe@x`. |
| Filters | **AND-only, single-valued, no ranges, no OR, no repeats.** Multiple values = multiple calls, merged client-side. |
| 504 ambiguity | 30s gateway timeout → 504, **but the request may have succeeded** — dangerous for non-idempotent POSTs; verify before retry. |
| Country codes | ISO 3166 alpha-2 **plus tax-region extensions** like `ES_CN` (Canary Is.), `GR_69` (Mt Athos). |

---

## 2. Endpoint map

**The `voucherlist` endpoint is the hub** — it is the only list/filter view over
sales documents and the only place the `overdue` status is derived. Per-resource
GETs return a bare object (no Pageable wrapper); there is **no GET-all** on any
sales-document type.

### Contacts (`research/contacts.md`) — the headline
- `GET /v1/contacts?email=&name=&number=&customer=&vendor=` — list (Pageable)
- `GET /v1/contacts/{id}` · `POST /v1/contacts` · `PUT /v1/contacts/{id}`
- **No DELETE.** `archived` is read-only (can't archive/unarchive via API).

### Sales documents (`research/invoices.md`, `research/sales-docs.md`)
Each of **invoices, quotations, order-confirmations, delivery-notes, credit-notes,
down-payment-invoices, dunnings**:
- `POST /v1/<type>` → creates a **draft**; `?finalize=true` finalizes (status `open`).
  Down-payment-invoices are **read-only** (can't create/edit). Dunnings ignore `finalize`.
- `POST /v1/<type>?precedingSalesVoucherId={id}` — **"pursue"** a preceding doc
  (the only "conversion"; invalid pursue → 406). Dunnings **require** it.
- `GET /v1/<type>/{id}` — one object (bare, not Pageable).
- `GET /v1/<type>/{id}/document` — **DEPRECATED** render → `{documentFileId}`.
- `GET /v1/<type>/{id}/file` — download PDF/XML binary (**preferred**; writes a file).
- **No list endpoint** — enumerate via `voucherlist`, then GET each by id.

### The hub + bookkeeping (`research/bookkeeping.md`)
- `GET /v1/voucherlist?voucherType=...&voucherStatus=...[&date filters]` — **list/filter
  everything.** `voucherType` comma-separated (e.g. `invoice,salesinvoice`).
- `GET /v1/payments/{voucherId}` — `openAmount`, `paymentStatus`, `paymentItems`.
- `GET/POST/PUT/DELETE /v1/vouchers` — bookkeeping vouchers (voucheritems).
- `GET /v1/posting-categories` · `GET /v1/payment-conditions` — reference.

### Reference & system (`research/reference-system.md`)
- `GET/POST/PUT/DELETE /v1/articles` — products/services (has DELETE, unlike contacts).
- `POST /v1/files` (multipart) · `GET /v1/files/{id}` (deprecated for sales docs).
- `GET /v1/profile` — org id, company, business features.
- `GET /v1/countries` · `GET /v1/print-layouts` — bare arrays (no wrapper).
- `GET /v1/recurring-templates[/{id}]` — **read-only** (no create/edit via API).
- `POST/GET/DELETE /v1/event-subscriptions` — webhooks; Lexware POSTs a callback
  payload to your `callbackUrl`.

---

## 3. The two status vocabularies (do not conflate)

- **Voucher RESOURCE** `voucherStatus`: `open, paid, paidoff, voided, transferred,
  sepadebit, unchecked` (+ blank). **No `overdue`.**
- **VOUCHERLIST** `voucherStatus`: `draft, open, paid, paidoff, voided, transferred,
  sepadebit, **overdue**, accepted, rejected, unchecked`.
- Per-**type** finalized enums differ again: quotation `accepted/rejected`,
  credit-note `paidoff`, dunning `draft`-only, etc. **Never reuse one type's status
  list for another** (see `research/sales-docs.md` for the per-type table).
- **`overdue` is transient/computed, never stored**, surfaces only in voucherlist,
  and **cannot be combined with other status values** in one filter call.

---

## 4. The killer feature — unanimous across all six agents

Every agent independently derived the same refused question. It is the clearest
killer-feature signal of the four tools.

> **"Who owes me money, how overdue, and who do I chase?"** — Outstanding
> Receivables / AR Aging. The API answers per-invoice and refuses every
> aggregate.

**How to derive it (the product):**
1. Page `voucherlist?voucherType=invoice,salesinvoice&voucherStatus=open,overdue,sepadebit`
   (respecting the 2/s throttle and the 10k window — slice by date).
2. Sum `openAmount` per row; roll up **per `contactId`**.
3. Compute **aging buckets 0–30 / 31–60 / 61–90 / 90+** from each `dueDate` vs today
   (`overdue` itself can't be filtered alongside other statuses, and buckets don't
   exist server-side at all).
4. Output the total, the per-customer breakdown, and the **dunning candidates**
   (open invoices past `dueDate` with no dunning yet — also refused server-side).

**Runner-up refused questions** (secondary commands, all confirmed by ≥2 agents):
- **Revenue for a period** (net/gross, by tax rate, by month) — no report; sum finalized vouchers.
- **Duplicate contacts / duplicate articles** — no dedup; pull corpus, compare VAT-ID/email/name (or GTIN/articleNumber).
- **Quote→invoice conversion rate & the full document chain** — `relatedVouchers` is one-hop and often empty; walk transitively.
- **MRR / recurring-revenue forecast** — recurring-templates have no aggregate or template→invoices link.
- **"What changed since X"** — no `updatedSince` delta on most collections (only voucherlist date filters + webhooks).
- **Contact hygiene** — companies missing VAT-ID, addresses missing countryCode, contacts un-editable because a list has >1 entry (see §5).

---

## 5. Gotchas that will shape the client & commands

- **Create returns an action-result, not the object.** POST/PUT on contacts (and
  sales docs) returns `{id, resourceUri, createdDate, updatedDate, version}` only.
  To learn the assigned customer/vendor **number** or see the object, **GET it
  after**. Build that follow-up into the create commands.
- **The "max-one-entry-per-list" write trap (contacts).** `addresses.billing/
  shipping`, every `emailAddresses.*`/`phoneNumbers.*` bucket, and
  `company.contactPersons` are arrays, but only **one** entry each is *writable*.
  A GET can return more; any PUT on such a contact fails with 406. The CLI must
  warn/handle this on edit.
- **`company` xor `person`** — exactly one, by object presence, not a type field.
- **Roles are presence-based** (`roles.customer`/`roles.vendor` existing = has it);
  ≥1 required; on create send **empty objects** `"customer": {}`.
- **Draft vs finalized is the semantic spine.** A draft is editable and not legally
  issued; finalizing is one-way (`?finalize=true`). Never present a draft as an
  issued invoice.
- **PDF is a two-step**, and `/{id}/document` is deprecated — use `/{id}/file`.
  Download writes a file (`--out`), the one non-JSON carve-out.
- **Doc transcription typos exist** (contacts create-response sample has a UUID
  with transposed segments that "in reality match"). Confirm shapes against a live
  key if granted before hard-coding anything subtle.
- **Country/tax edge codes** (`ES_CN`, `GR_69`), **XRechnung pairing** (`buyerReference`
  ⇒ `vendorNumberAtCustomer`), **reverse-charge** tax types (`constructionService13b`)
  — real fields in the examples; don't drop them.

---

## 6. Family-fit notes

- **Pagination = OpenProject's stop-rule** (authoritative total), NOT drone's.
- **Optimistic locking = OpenProject's `lockVersion`** pattern (read-modify-write).
- **Rate limit is the new challenge** — no sibling had to self-throttle. The client
  needs a token bucket, and fan-out commands (the receivables sweep) must pace.
- **Three error envelopes** — the mapper is more complex than any sibling's; test
  all three shapes with fixtures from `research/conventions.md`.
- **No local instance** — captured examples are the fixtures; a one-time live
  read-only confirmation pass replaces the "spike against a real server" step.

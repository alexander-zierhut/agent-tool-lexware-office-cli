# Response examples — the fixture manifest

**These verbatim JSON examples are the hermetic-test fixture corpus for `lexware-cli`.**
Lexware Office has no self-hostable test instance, so instead of booting a server we feed
these (captured from the official docs, 2026-07-18) to a hand-rolled fake client. Each is
real doc sample data (synthetic UUIDs/German sample names) — safe to commit, no live org data.

Full context for every example — the endpoint, the surrounding notes, the field semantics —
is in the per-area file named below. This manifest is the index + parse-validation.


## `bookkeeping.md`

- ✅ 1. Voucher object — multi-item, different tax rates, collective contact (GET /v1  — 1243b, ok
- ✅ 2. Create a Voucher — request body (POST /v1/vouchers)  — 464b, ok
- ✅ 3. Create a Voucher — response (POST /v1/vouchers → 201)  — 259b, ok
- ✅ 4. Retrieve a Voucher — response (GET /v1/vouchers/{id})  — 797b, ok
- ✅ 5. Filter vouchers by number — Pageable response (GET /v1/vouchers?voucherNumber  — 1755b, ok
- ✅ This is the killer-feature source: open / paid / overdue documents across all ty  — 2359b, ok
- ▫︎ 7. Payments — four samples for different voucher types (shape of GET /v1/payment  — 1524b, fragment/elided
- ✅ 8. Payments — retrieve response (GET /v1/payments/1f1dc13c-fd68-11ea-a8b9-ff40c7  — 480b, ok
- ✅ 9. Payment Conditions — list response (GET /v1/payment-conditions)  — 564b, ok
- ✅ 10. Posting Categories — list response (GET /v1/posting-categories)  — 816b, ok
- ▫︎ 11. Generic Pageable envelope (from "Paging of Resources")  — 338b, fragment/elided

## `contacts.md`

- ✅ GET a full company contact (roles customer + vendor) — "Contact Properties" samp  — 1725b, ok
- ✅ GET a private-person contact — "Person Details" sample  — 311b, ok
- ✅ POST /v1/contacts — create response (action-result, NOT the full contact)  — 259b, ok
- ✅ GET /v1/contacts/{id} — retrieve response  — 332b, ok
- ✅ GET /v1/contacts?page=0 — paginated list response (Spring Pageable wrapper)  — 1064b, ok

## `conventions.md`

- ▫︎ 1. Pagination — `Pageable` wrapper (canonical, empty content)  — 338b, fragment/elided
- ✅ 2. Pagination — real populated page (contacts list)  — 966b, ok
- ✅ 3. Pagination — populated page with money & enums (articles list)  — 1580b, ok
- ▫︎ 4. Money shape inside vouchers (unitPrice / totalPrice / taxAmounts)  — 102b, fragment/elided
- ▫︎ 4. Money shape inside vouchers (unitPrice / totalPrice / taxAmounts)  — 111b, fragment/elided
- ▫︎ 4. Money shape inside vouchers (unitPrice / totalPrice / taxAmounts)  — 144b, fragment/elided
- ✅ 5. Error envelope — "Regular" error response (used by most endpoints)  — 405b, ok
- ✅ 6. Error envelope — "Legacy" error response (contacts, files, vouchers only)  — 189b, ok
- ✅ 7. Error envelope — Authorization / Connection errors (gateway-level)  — 30b, ok
- ✅ 7. Error envelope — Authorization / Connection errors (gateway-level)  — 128b, ok
- ✅ 7. Error envelope — Authorization / Connection errors (gateway-level)  — 62b, ok
- ✅ 7. Error envelope — Authorization / Connection errors (gateway-level)  — 44b, ok

## `invoices.md`

- ✅ GET /v1/invoices/{id} — full invoice object (Invoices Properties sample)  — 3945b, ok
- ✅ GET /v1/invoices/{id} — second retrieve sample (from "Retrieve an Invoice")  — 2952b, ok
- ✅ POST /v1/invoices — create response  — 259b, ok
- ✅ GET /v1/invoices/{id}/document — render PDF (DEPRECATED)  — 63b, ok
- ✅ POST /v1/files — upload (bookkeeping voucher) + response  — 106b, ok
- ✅ GET /v1/voucherlist — list/filter invoices (the only list endpoint)  — 2359b, ok
- ▫︎ GET /v1/payments/{voucherId} — payment status samples (Payments Properties)  — 1524b, fragment/elided
- ✅ GET /v1/payments/{voucherId} — payment status samples (Payments Properties)  — 480b, ok
- ▫︎ taxConditions — vat-free (Reverse Charge) sample  — 146b, fragment/elided
- ✅ Error responses (invoices use the "regular" error format)  — 405b, ok
- ✅ Error responses (invoices use the "regular" error format)  — 189b, ok

## `reference-system.md`

- ✅ GET `/v1/articles/{id}` — full "Article Properties" sample (all fields populated  — 678b, ok
- ✅ POST `/v1/articles` — action-result on create  — 269b, ok
- ✅ GET `/v1/articles/{id}` — retrieve response (note: no `organizationId`/`createdD  — 497b, ok
- ✅ PUT `/v1/articles/{id}` — action-result on update  — 259b, ok
- ✅ GET `/v1/articles?page=0` — list (Pageable wrapper)  — 1580b, ok
- ✅ GET `/v1/countries` — bare array  — 509b, ok
- ✅ GET `/v1/print-layouts` — bare array  — 250b, ok
- ✅ GET `/v1/profile` — profile response  — 565b, ok
- ✅ POST `/v1/files` — upload response (HTTP 202)  — 106b, ok
- ✅ Event subscription — "Event Subscriptions Properties" sample (entity shape)  — 255b, ok
- ✅ Webhook callback payload (Lexware → your `callbackUrl`, HTTP POST)  — 201b, ok
- ✅ POST `/v1/event-subscriptions` — create response (HTTP 201, action-result)  — 280b, ok
- ✅ GET `/v1/event-subscriptions/{subscriptionId}` — retrieve one  — 265b, ok
- ✅ GET `/v1/event-subscriptions` — retrieve all (content-wrapped, no paging metadat  — 348b, ok
- ✅ GET `/v1/recurring-templates/{id}` — full "Recurring Template Properties" sample  — 3621b, ok
- ▫︎ GET `/v1/recurring-templates/{id}` — full "Recurring Template Properties" sample  — 146b, fragment/elided
- ▫︎ GET `/v1/recurring-templates/{id}` — retrieve sample (settings TRUNCATED in the   — 1749b, fragment/elided
- ✅ GET `/v1/recurring-templates?page=0&size=25&sort=createdDate,DESC` — collection   — 3383b, ok

## `sales-docs.md`

- ✅ Quotation — `GET /v1/quotations/424f784e-1f4e-439e-8f71-19673e6d6583`  — 4060b, ok
- ✅ Order Confirmation — `GET /v1/order-confirmations/e9066f04-8cc7-4616-93f8-ac9ecc  — 3192b, ok
- ✅ Credit Note — `GET /v1/credit-notes/e9066f04-8cc7-4616-93f8-ac9ecc8479c8`  — 2283b, ok
- ✅ Delivery Note — `GET /v1/delivery-notes/e9066f04-8cc7-4616-93f8-ac9ecc8479c8`  — 1838b, ok
- ✅ Dunning — `GET /v1/dunnings/a54820ca-ea27-11eb-8703-dffc93413c04`  — 2134b, ok
- ✅ Down Payment Invoice — `GET /v1/down-payment-invoices/28af0062-5b19-11eb-9609-57  — 1920b, ok
- ✅ Shared: create response envelope (POST 201) — same shape for all writable types  — 261b, ok
- ✅ Shared: render-document response — `GET /v1/{type}/{id}/document`  — 63b, ok
- ▫︎ Shared: vat-free (reverse-charge) taxConditions snippet  — 146b, fragment/elided

---

**Totals: 55 standalone-parseable examples + 11 illustrative fragments
(elided arrays / sub-object snippets). Use the parseable ones directly as fixtures; the
fragments show a single field's shape in context.**

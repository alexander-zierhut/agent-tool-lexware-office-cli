# Live confirmation pass — Lexware Office SANDBOX

Probed **2026-07-18** against a real, manually-provisioned sandbox
(org "Zierhut IT GmbH", `taxType: net`, features INVOICING/BOOKKEEPING/INVOICING_PRO).
This is the "observation beats the docs" pass the playbook demands. **Where this
file and the doc-derived `API_MAP.md` / `RESPONSE_EXAMPLES.md` disagree, THIS
wins** — it is measured, not read.

Sandbox API base: **`https://api.lexware-sandbox.io`** (prod is `https://api.lexware.io`;
the `.de` variants do not resolve). The sandbox key management UI is
`https://app.lexware-sandbox.de/addons/public-api`. The key lives only in the
gitignored `.env`; it is never committed and never printed.

---

## 0. THE headline requirement: the client MUST rate-limit AND retry

Confirmed the hard way — a burst of ~6 quick requests earned an immediate
`HTTP 429 {"message":"Rate limit exceeded"}`, and a single request after a pause
succeeded. Pacing every call to **≥0.7 s apart (~1.4/s, under the 2/s ceiling)**
ran the entire fill with **zero** further 429s. This is not optional; it is how
the API works. The CLI's `client.py` must ship **both** halves:

**(a) Proactive rate limiting — a token bucket.** There are **no `X-RateLimit-*`
or `Retry-After` headers**, so the client cannot react its way to correctness; it
must not *emit* more than the budget. Target **≤ ~1.5 req/s** (leave headroom —
jitter means even exactly-2/s gets throttled). Every request goes through the
limiter, including each page of a paginated sweep. The AR-aging sweep and any
fan-out command inherit this for free by routing through the one client.

**(b) Reactive retry — backoff on 429.** On 429, **exponential backoff with
jitter** and retry (a few attempts, cap the total wait). Two live subtleties the
retry logic must encode:
  - **A 429 can arrive disguised as HTTP 500** whose body says *"Internal server
    error or rate limit exceeded"* — treat that specific 500 as retryable rate-limit,
    not a hard error. (Documented by the conventions agent; consistent with the
    gateway-level `{"message": ...}` shape seen live.)
  - **504 gateway timeouts may have SUCCEEDED** (30 s gateway). Do **not** blindly
    retry a non-idempotent POST on 504 — for writes, verify (GET) before retrying,
    or the client double-creates an invoice.

Concretely, `client.py` wants: a small token-bucket gate before send; a retry loop
that catches `429`, the `500`-rate-limit body, and connection errors; idempotency
awareness on `POST`. The paced `request()` used for this spike is the working
prototype — port its shape.

---

## 1. Confirmed exactly as the docs said

- **Auth**: `Authorization: Bearer <key>` ✓. `GET /v1/profile` returns
  `{organizationId, businessFeatures[], companyName, connectionId, created{date,userEmail,userId,userName}, smallBusiness, taxType}`.
- **Contact POST → action-result only**: `{id, resourceUri, createdDate, updatedDate, version}`,
  NOT the full contact. `version` goes `0` (create) → `1`. ✓
- **The contact OBJECT has no `createdDate`/`updatedDate`** on GET — timestamps live
  only in the action-result. GET keys: `[addresses, archived, company, emailAddresses, id, organizationId, roles, version]`. ✓
- **Customer/vendor `number` is server-assigned and read-only** (first customer got `10002`),
  absent from the create result — you must GET the contact to learn it. ✓
- **`voucherlist` is a Pageable wrapper**, default sort `voucherdate DESC`. ✓
- **`overdue` is a transient sub-state of `open`.** Filtering `voucherStatus=open`
  returned 4 rows, **3 of them with `voucherStatus: overdue`**; filtering
  `voucherStatus=overdue` returned exactly those 3. ✓ (This is the crux of the
  killer feature and it behaves precisely as captured.)
- **Regular error envelope** on a bad `GET /v1/articles`:
  `{timestamp, status, error, path, traceId, requestId, message, details?}`. ✓
- **Net→gross VAT computed server-side**: net 2500 → gross 2975 at 19%. ✓

## 2. CORRECTIONS to the doc-derived research (observation wins)

1. **HTTP success codes differ per resource.** `POST /v1/contacts` → **200**;
   `POST /v1/invoices` and `POST /v1/quotations` → **201**. The research treated the
   action-result uniformly; the status code is not uniform. The client must not
   assume 200 == created.
2. **Stale-version conflict is `HTTP 406`, not `409`.** A PUT on a contact with an
   old `version` returned **406** with the **legacy `IssueList` envelope**:
   `{"requestId": "...", "IssueList": [{"i18nKey": "invalid_value", "source": "version", "type": "validation_failure"}]}`.
   The docs/agents said "409 Conflict". **The error mapper must therefore inspect
   the body, not just the status** — a 406 whose `IssueList[].source == "version"`
   is a CONFLICT (exit 6), while a 406 for other fields is VALIDATION (exit 7).
   (May differ for the regular-envelope resources; only contacts tested — treat
   409 AND "406+source=version" both as conflict.)
3. **`voucherlist` REQUIRES a `voucherStatus`.** `GET /v1/voucherlist?voucherType=invoice`
   with no status → **HTTP 400**. You cannot list "all invoices of a type" in one
   call; the CLI must always pass a status (or sweep the known statuses and merge).
4. **`voucherlist` rows are SELF-SUFFICIENT for AR aging** — no per-invoice GET
   needed. A row carries: `{id, voucherType, voucherStatus, voucherNumber,
   voucherDate, createdDate, updatedDate, dueDate, contactId, contactName,
   totalAmount, openAmount, currency, archived}`. The research implied you'd GET
   each document; reality is far cheaper — **one paged sweep + client-side
   bucketing** builds the whole receivables report. This also keeps the feature
   comfortably inside the 2/s budget (page count, not invoice count).
5. **Article `type` is UPPERCASE enum `PRODUCT` | `SERVICE`** (line-item `type` is
   lowercase like `custom`/`service`/`material` — do not conflate the two). A bad
   article type → **HTTP 400** (`"Value must be one of: [PRODUCT, SERVICE]"`), i.e.
   articles use **400** for enum validation while contacts use **406** — another
   per-resource status difference for the error mapper.

## 3. Sandbox state after the fill (for building/testing against)

Reference data pre-loaded: **257 countries** (each `{countryCode, countryNameEN,
countryNameDE, taxClassification}`), **231 posting-categories**, **1 payment-condition**.

Created (all synthetic "Muster/Beispiel" German sample data — no real customers):
- **5 contacts**: 3 customers (2 company, 1 person), 1 vendor, 1 both-roles.
- **5 invoices** exercising the AR-aging feature end to end:
  - 1 **draft** (~€800 net)
  - 1 **open, current** (RE26426, due +9 d, €2975 open)
  - 3 **overdue** at ~**15 / 46 / 95 days** past due (€535.50 / €1428 / €1166.20 open)
  - → total outstanding ≈ **€6104.70**, of which ≈ **€3129.70 overdue**, spread across
    the 0-30 / 31-60 / 90+ buckets. A real, non-trivial fixture for the AR command.
- **1 quotation** (draft, €5000 net, expires +31 d).
- (Articles: 2 attempted; the first pass used lowercase `type` and 400'd — see §2.5;
  re-create with `PRODUCT`/`SERVICE`.)

## 4. Open items / where the user may need to help

- **A "paid" invoice example is missing.** Recording a payment appears to be a
  bank-reconciliation action, likely NOT writable via the public API (payments are
  read via `GET /v1/payments/{id}`). To get a `paid`/`paidoff` fixture we probably
  need the invoice marked paid **in the sandbox UI**, or to confirm no API path
  exists. Worth asking the user.
- **Articles list quirk**: `GET /v1/articles?page=0&size=1` returned **406** — the
  list endpoint may reject bare paging params or need a filter; nail down the exact
  list contract before building `article list`.
- Not yet exercised live: dunnings, credit-notes (pursue flow), delivery-notes,
  down-payment-invoices, files/PDF render+download, event-subscriptions (webhooks),
  recurring-templates. Their shapes are in `research/*.md`; confirm on a later pass.

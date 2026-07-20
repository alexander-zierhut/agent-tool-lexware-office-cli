# Command reference

_Auto-generated from the CLI (`python scripts/gen_docs.py`)._

_Every command also accepts `--output/-o` (json\|table\|markdown\|csv), `--format/-f`, `--fields`/`--columns`, `--dry-run`, `--stream` and `--no-context`. Those are **stripped from argv before parsing**, so they work anywhere on the line — before or after the subcommand. `--profile/-p` and `--no-color` are ordinary root options and must therefore come **before** the subcommand (`lexware-office -p prod invoice ls`, not `lexware-office invoice ls -p prod`)._

## Groups

- [`article`](#article) — Articles: products & services catalogue.
- [`auth`](#auth) — Log in, log out, inspect credentials.
- [`contact`](#contact) — Customers & vendors: list, get, create, update.
- [`context`](#context) — Sticky session defaults, per profile.
- [`credit-note`](#credit-note) — Credit notes (Gutschriften).
- [`delivery-note`](#delivery-note) — Delivery notes (Lieferscheine).
- [`down-payment-invoice`](#down-payment-invoice) — Down-payment invoices (read-only).
- [`dunning`](#dunning) — Dunnings (Mahnungen) — require a preceding invoice.
- [`file`](#file) — Download stored files by id.
- [`guide`](#guide) — Built-in operating guide — how to use this CLI without external docs.
- [`install`](#install) — Integrate with other tools (e.g. `install claude`).
- [`invoice`](#invoice) — Invoices: list, get, create, finalize, payments, PDF.
- [`order-confirmation`](#order-confirmation) — Order confirmations (Auftragsbestätigungen).
- [`profile`](#profile) — The connected organisation — and what your key can do.
- [`quotation`](#quotation) — Quotations (Angebote): list, get, create, PDF.
- [`raw`](#raw) — Escape hatch: call any API path directly.
- [`receivables`](#receivables) — Outstanding receivables + AR aging — the number the API won't total.
- [`recurring`](#recurring) — Recurring invoice templates (read-only).
- [`reference`](#reference) — Reference data: countries, categories, payment conditions.
- [`report`](#report) — Report a bug or missing feature — prints this tool's repo and a pre-filled issue link (offline, no token).
- [`settings`](#settings) — View & change CLI settings.
- [`voucher`](#voucher) — Bookkeeping vouchers (accounting entries).
- [`webhook`](#webhook) — Webhooks: subscribe to events, list, delete.

## `article`

### `lexware-office article create`

Create a product/service article. `type` is uppercase PRODUCT|SERVICE.

| Option | Description |
| --- | --- |
| `--title` |  **(required)** |
| `--type` | PRODUCT \| SERVICE (uppercase). |
| `--net` | Net price (EUR). **(required)** |
| `--tax` | Tax rate percent. |
| `--unit` |  |
| `--number` | articleNumber. |

### `lexware-office article delete`

Delete an article.

**Arguments:** `article_id` (required)

| Option | Description |
| --- | --- |
| `--yes`, `-y` |  |

### `lexware-office article get`

Retrieve one article.

**Arguments:** `article_id` (required)

### `lexware-office article list`

List articles (paginated).

| Option | Description |
| --- | --- |
| `--number` | Filter by articleNumber. |
| `--gtin` | Filter by GTIN. |
| `--limit` |  |

## `auth`

### `lexware-office auth login`

Store an API key for a profile, after verifying it against `/v1/profile`.

| Option | Description |
| --- | --- |
| `--profile`, `-p` | Profile name (default: 'default'). |
| `--token` | API key (else prompted). |
| `--sandbox` | Use the sandbox API (api.lexware-sandbox.io). |
| `--url` | Override the API base URL. |

### `lexware-office auth logout`

Delete the stored key for a profile.

| Option | Description |
| --- | --- |
| `--profile`, `-p` |  |

### `lexware-office auth status`

Which key/backend is in use, and for which organisation.

## `contact`

### `lexware-office contact create`

Create a contact. Returns the action-result; the assigned customer/vendor
number is fetched and included (the create result omits it).

| Option | Description |
| --- | --- |
| `--company` | Company name (company contact). |
| `--first-name` |  |
| `--last-name` |  |
| `--role` | customer \| vendor \| both. |

### `lexware-office contact get`

Retrieve one contact (the full object, incl. the assigned number).

**Arguments:** `contact_id` (required)

### `lexware-office contact list`

List contacts (paginated + paced automatically).

| Option | Description |
| --- | --- |
| `--customer` | Only customers. |
| `--vendor` | Only vendors. |
| `--name` | Name filter (>=3 chars, substring). |
| `--email` | Email filter (>=3 chars, substring). |
| `--limit` | Max contacts to return (0 = all). |

### `lexware-office contact update`

Update a contact (read-modify-write; the version is handled for you).

Note the API's max-ONE-entry-per-list rule: a contact whose email/phone/address
lists already hold more than one entry cannot be PUT — the server rejects it.
This command re-sends the current object with your change and the current
version; a stale version is a conflict (exit 6).

**Arguments:** `contact_id` (required)

| Option | Description |
| --- | --- |
| `--company` | New company name. |

## `context`

### `lexware-office context clear`

### `lexware-office context set`

| Option | Description |
| --- | --- |
| `--contact` | Default contact id. |

### `lexware-office context show`

## `credit-note`

### `lexware-office credit-note create`

Create the document (draft by default; --finalize issues it).

| Option | Description |
| --- | --- |
| `--contact` | Contact id. **(required)** |
| `--item` | Line item name. **(required)** |
| `--net` | Net unit price (EUR). Omit for delivery notes. |
| `--tax` | Tax rate percent. |
| `--qty` |  |
| `--preceding` | Preceding sales-voucher id (pursue / required for dunnings). |
| `--finalize` | Finalize immediately (assigns a number; one-way). |

### `lexware-office credit-note get`

Retrieve one document (the full object).

**Arguments:** `doc_id` (required)

### `lexware-office credit-note list`

List via the voucherlist hub (the only list view; a status is required).

| Option | Description |
| --- | --- |
| `--status` | draft \| open \| ... (voucherlist status). |
| `--limit` | Max results (0 = all). |

### `lexware-office credit-note pdf`

Download the document's PDF (must be finalized).

**Arguments:** `doc_id` (required)

| Option | Description |
| --- | --- |
| `--out` | Where to save the PDF. |
| `--open` | Open in the system viewer (no-ops headless). |

## `delivery-note`

### `lexware-office delivery-note create`

Create the document (draft by default; --finalize issues it).

| Option | Description |
| --- | --- |
| `--contact` | Contact id. **(required)** |
| `--item` | Line item name. **(required)** |
| `--net` | Net unit price (EUR). Omit for delivery notes. |
| `--tax` | Tax rate percent. |
| `--qty` |  |
| `--preceding` | Preceding sales-voucher id (pursue / required for dunnings). |
| `--finalize` | Finalize immediately (assigns a number; one-way). |

### `lexware-office delivery-note get`

Retrieve one document (the full object).

**Arguments:** `doc_id` (required)

### `lexware-office delivery-note list`

List via the voucherlist hub (the only list view; a status is required).

| Option | Description |
| --- | --- |
| `--status` | draft \| open \| ... (voucherlist status). |
| `--limit` | Max results (0 = all). |

## `down-payment-invoice`

### `lexware-office down-payment-invoice create`

(read-only resource).

### `lexware-office down-payment-invoice get`

Retrieve one document (the full object).

**Arguments:** `doc_id` (required)

### `lexware-office down-payment-invoice list`

List via the voucherlist hub (the only list view; a status is required).

| Option | Description |
| --- | --- |
| `--status` | draft \| open \| ... (voucherlist status). |
| `--limit` | Max results (0 = all). |

## `dunning`

### `lexware-office dunning create`

Create the document (draft by default; --finalize issues it).

| Option | Description |
| --- | --- |
| `--contact` | Contact id. **(required)** |
| `--item` | Line item name. **(required)** |
| `--net` | Net unit price (EUR). Omit for delivery notes. |
| `--tax` | Tax rate percent. |
| `--qty` |  |
| `--preceding` | Preceding sales-voucher id (pursue / required for dunnings). |
| `--finalize` | Finalize immediately (assigns a number; one-way). |

### `lexware-office dunning get`

Retrieve one document (the full object).

**Arguments:** `doc_id` (required)

### `lexware-office dunning list`

List via the voucherlist hub (the only list view; a status is required).

| Option | Description |
| --- | --- |
| `--status` | draft \| open \| ... (voucherlist status). |
| `--limit` | Max results (0 = all). |

### `lexware-office dunning pdf`

Download the document's PDF (must be finalized).

**Arguments:** `doc_id` (required)

| Option | Description |
| --- | --- |
| `--out` | Where to save the PDF. |
| `--open` | Open in the system viewer (no-ops headless). |

## `file`

### `lexware-office file download`

Download a file by id to `--out`. Binary carve-out — the JSON reports the path.

**Arguments:** `file_id` (required)

| Option | Description |
| --- | --- |
| `--out` | Where to save the file. **(required)** |

## `guide`

### `lexware-office guide`

Built-in operating guide — how to use this CLI without external docs.

**Arguments:** `topic` (optional)

## `install`

### `lexware-office install claude`

Register `lexware-office` with Claude Code as a Skill. Reversible with --uninstall.

| Option | Description |
| --- | --- |
| `--project` | Install into ./.claude instead of ~/.claude. |
| `--memory` | Also add a one-line hint to ~/.claude/CLAUDE.md. |
| `--force` | Install even if Claude Code isn't detected. |
| `--uninstall` | Remove the skill (and memory hint). |
| `--print` | Print the SKILL.md that would be written and exit. |

## `invoice`

### `lexware-office invoice create`

Create an invoice (draft by default; `--finalize` issues it).

| Option | Description |
| --- | --- |
| `--contact` | Customer contact id. **(required)** |
| `--item` | Line item name. **(required)** |
| `--net` | Net unit price (EUR). **(required)** |
| `--tax` | Tax rate percent. |
| `--qty` |  |
| `--term-days` | Payment term (days) -> due date. |
| `--finalize` | Finalize immediately (assigns a number, one-way). |

### `lexware-office invoice finalize`

Finalize a draft invoice (assigns a number, makes it legally issued).

One-way and legally significant — there is no un-finalize.

**Arguments:** `invoice_id` (required)

### `lexware-office invoice get`

Retrieve one invoice (the full object).

**Arguments:** `invoice_id` (required)

### `lexware-office invoice list`

List invoices via the voucherlist hub (the only list view). A status is
required by the API; defaults to `open`. Rows carry contact/due/open amounts.

| Option | Description |
| --- | --- |
| `--status` | draft \| open \| overdue \| paid \| voided. |
| `--limit` | Max invoices (0 = all). |

### `lexware-office invoice payments`

Payment status of an invoice: what's open, what's been paid, and how.

Reports `openAmount`, `paymentStatus` (balanced | openRevenue) and the payment
items. Note this shows the STORED status (`open`), never the derived `overdue`
— aging lives only in `receivables` / `invoice list`.

**Arguments:** `invoice_id` (required)

### `lexware-office invoice pdf`

Download an invoice's PDF, and optionally open it for preview.

A draft cannot be rendered (the API returns 409) — finalize it first. The PDF
is the one binary carve-out: it is written to a file and the JSON reports the
path, never dumped to stdout.

**Arguments:** `invoice_id` (required)

| Option | Description |
| --- | --- |
| `--out` | Where to save the PDF (default: ./<voucherNumber>.pdf). |
| `--open` | Open the PDF in the system viewer (human affordance; no-ops headless). |

## `order-confirmation`

### `lexware-office order-confirmation create`

Create the document (draft by default; --finalize issues it).

| Option | Description |
| --- | --- |
| `--contact` | Contact id. **(required)** |
| `--item` | Line item name. **(required)** |
| `--net` | Net unit price (EUR). Omit for delivery notes. |
| `--tax` | Tax rate percent. |
| `--qty` |  |
| `--preceding` | Preceding sales-voucher id (pursue / required for dunnings). |
| `--finalize` | Finalize immediately (assigns a number; one-way). |

### `lexware-office order-confirmation get`

Retrieve one document (the full object).

**Arguments:** `doc_id` (required)

### `lexware-office order-confirmation list`

List via the voucherlist hub (the only list view; a status is required).

| Option | Description |
| --- | --- |
| `--status` | draft \| open \| ... (voucherlist status). |
| `--limit` | Max results (0 = all). |

### `lexware-office order-confirmation pdf`

Download the document's PDF (must be finalized).

**Arguments:** `doc_id` (required)

| Option | Description |
| --- | --- |
| `--out` | Where to save the PDF. |
| `--open` | Open in the system viewer (no-ops headless). |

## `profile`

### `lexware-office profile doctor`

Diagnose the connection: is the key valid, which org, what features?

Never raises — returning the report is its job.

### `lexware-office profile show`

The connected organisation (`GET /v1/profile`): company, features, tax type.

## `quotation`

### `lexware-office quotation create`

Create the document (draft by default; --finalize issues it).

| Option | Description |
| --- | --- |
| `--contact` | Contact id. **(required)** |
| `--item` | Line item name. **(required)** |
| `--net` | Net unit price (EUR). Omit for delivery notes. |
| `--tax` | Tax rate percent. |
| `--qty` |  |
| `--preceding` | Preceding sales-voucher id (pursue / required for dunnings). |
| `--finalize` | Finalize immediately (assigns a number; one-way). |

### `lexware-office quotation get`

Retrieve one document (the full object).

**Arguments:** `doc_id` (required)

### `lexware-office quotation list`

List via the voucherlist hub (the only list view; a status is required).

| Option | Description |
| --- | --- |
| `--status` | draft \| open \| ... (voucherlist status). |
| `--limit` | Max results (0 = all). |

### `lexware-office quotation pdf`

Download the document's PDF (must be finalized).

**Arguments:** `doc_id` (required)

| Option | Description |
| --- | --- |
| `--out` | Where to save the PDF. |
| `--open` | Open in the system viewer (no-ops headless). |

## `raw`

### `lexware-office raw delete`

DELETE any path.

**Arguments:** `path` (required)

### `lexware-office raw get`

GET any path (relative to /v1). Example: `raw get /countries`.

**Arguments:** `path` (required)

| Option | Description |
| --- | --- |
| `--param` |  |

### `lexware-office raw post`

POST any path with a JSON --data body.

**Arguments:** `path` (required)

| Option | Description |
| --- | --- |
| `--data` |  |
| `--param` |  |

### `lexware-office raw put`

PUT any path with a JSON --data body.

**Arguments:** `path` (required)

| Option | Description |
| --- | --- |
| `--data` |  |

## `receivables`

### `lexware-office receivables`

Outstanding receivables + AR aging — the number the API won't total.

| Option | Description |
| --- | --- |
| `--view` | aging \| customers \| dunning |
| `--min-days` | For --view dunning: only invoices at least this many days overdue. |
| `--exit-code` | Exit 20 if anything is overdue (for scripts/CI). |

## `recurring`

### `lexware-office recurring get`

Retrieve one recurring template.

**Arguments:** `template_id` (required)

### `lexware-office recurring list`

List recurring templates (paginated).

| Option | Description |
| --- | --- |
| `--limit` |  |

## `reference`

### `lexware-office reference countries`

ISO countries with their tax classification (de / intraCommunity / thirdPartyCountry).

### `lexware-office reference payment-conditions`

The organisation's payment-term templates.

### `lexware-office reference posting-categories`

Booking categories for vouchers (income vs outgo).

### `lexware-office reference print-layouts`

Document print layouts available to the organisation.

## `report`

### `lexware-office report`

Report a bug or missing feature — prints this tool's repo and a pre-filled issue link (offline, no token).

## `settings`

### `lexware-office settings path`

### `lexware-office settings set-format`

**Arguments:** `fmt` (required)

### `lexware-office settings show`

## `voucher`

### `lexware-office voucher delete`

Delete a bookkeeping voucher.

**Arguments:** `voucher_id` (required)

| Option | Description |
| --- | --- |
| `--yes`, `-y` |  |

### `lexware-office voucher get`

Retrieve one bookkeeping voucher.

**Arguments:** `voucher_id` (required)

### `lexware-office voucher list`

List bookkeeping vouchers (paginated).

| Option | Description |
| --- | --- |
| `--number` | Filter by voucherNumber. |
| `--limit` |  |

## `webhook`

### `lexware-office webhook delete`

Delete a webhook subscription (stop receiving that event).

**Arguments:** `subscription_id` (required)

| Option | Description |
| --- | --- |
| `--yes`, `-y` | Skip the confirmation. |

### `lexware-office webhook events`

List the event types you can subscribe to.

### `lexware-office webhook get`

Retrieve one subscription.

**Arguments:** `subscription_id` (required)

### `lexware-office webhook list`

List all webhook subscriptions.

### `lexware-office webhook subscribe`

Subscribe to an event — register a callback URL Lexware will POST to.

Preview with `--dry-run`. The callback must be a reachable HTTPS endpoint;
Lexware sends the event id + affected resource id, and you fetch the detail.

| Option | Description |
| --- | --- |
| `--event` | Event type, e.g. invoice.created. Known: contact.created, contact.changed, contact.deleted, invoice.created, invoice.changed, invoice.deleted, … **(required)** |
| `--url` | Your HTTPS callback URL; Lexware POSTs the event here. **(required)** |


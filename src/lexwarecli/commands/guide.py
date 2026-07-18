"""`lexware-cli guide` — the built-in operating manual.

Works with no config, no key and no network — it is what an agent runs first.
"""

from __future__ import annotations

import typer

OVERVIEW = """\
lexware-cli — operating guide (run `lexware-cli guide <topic>` for details)

WHAT IT IS
  A CLI for Lexware Office (invoicing/bookkeeping SaaS): customers & vendors,
  invoices, and the receivables/AR-aging the API refuses to total. Built for AI
  agents. NOT payroll or banking — the API has neither.

OUTPUT CONTRACT
  - stdout is JSON. Errors are JSON on stderr with a non-zero exit code.
  - EXCEPTION: `invoice pdf` writes a PDF file; the JSON reports its path.
  - Exit codes: 0 ok · 1 generic · 3 config · 4 auth · 5 not-found · 6 conflict ·
                7 validation · 8 rate-limited · 130 interrupted.
  - `-o table|markdown|csv`, `--fields a,b`, `--stream`, `--dry-run` (preview writes).
  - Findings are not failures: `receivables` exits 0 even with money overdue; add
    `--exit-code` to get exit 20 when something is overdue.

AUTHENTICATE
  Interactive:   lexware-cli auth login            (shows where to get a key)
                 lexware-cli auth login --sandbox   (the test API)
  Headless:      export LEXWARE_API_KEY=xxxxxxxx
                 export LEXWARE_URL=https://api.lexware-sandbox.io   # sandbox only
  Get a key:     <your-lexware>/addons/public-api
  Check:         lexware-cli auth status   (names which key/backend is in use)

THE ONE THING TO KNOW: THE CLIENT PACES ITSELF
  The API allows ~2 requests/second org-wide and sends no rate-limit headers, so
  the client tracks the budget and AUTO-DELAYS every request to stay under it. You
  never manage this — a big `receivables` sweep just takes a little longer. On the
  rare 429 (a shared budget) it backs off and retries; exit 8 means it gave up.

START HERE
  lexware-cli receivables              # who owes me money + AR aging (the point)
  lexware-cli receivables --view customers
  lexware-cli receivables --view dunning     # who to chase, worst first
  lexware-cli invoice list --status overdue
  lexware-cli contact list --customer

COMMAND GROUPS (run `lexware-cli <group> --help` for any)
  receivables · invoice · contact · quotation · credit-note · order-confirmation ·
  delivery-note · down-payment-invoice · dunning · article · voucher · webhook ·
  reference · recurring · file · profile · auth · raw · settings · context · install

KEY GOTCHAS (each verified against the real API — save yourself a wrong answer)
  - `overdue` exists ONLY in the invoice LIST (voucherlist); a single invoice's
    own status stays `open`. Aging comes from the due date, not the status.
  - Sum openAmount, NOT the total: a partial payment lowers what's owed while the
    invoice may still be overdue (status and balance are independent).
  - Sales documents come as DRAFTS; finalizing (assigning a number, issuing them)
    is ONE-WAY. A draft can't be turned into a PDF (finalize first).
  - Create returns only an action-result {id, ...}, not the object; `get` it to see
    the assigned customer/vendor number.
  - Money is gross/net with tax; amounts are decimals, not to be re-rounded.

TOPICS:  receivables · invoices · documents · webhooks · contacts · auth · pacing · output · gotchas
"""

TOPICS: dict[str, str] = {
    "receivables": """\
RECEIVABLES — the killer feature ("who owes me money?")

  lexware-cli receivables                     # AR aging ladder + totals
  lexware-cli receivables --view customers    # per-customer rollup, worst first
  lexware-cli receivables --view dunning      # overdue invoices to chase
  lexware-cli receivables --view dunning --min-days 14
  lexware-cli receivables --exit-code         # exit 20 if anything is overdue

  The API answers per-invoice and refuses the aggregate. This sweeps the invoice
  list once (paced automatically), sums **openAmount** per customer, and ages each
  invoice into 0-30 / 31-60 / 61-90 / 90+ buckets from its due date. `overdue`
  itself is a list-only derived status, so aging is computed here, not read.
""",
    "invoices": """\
INVOICES

  lexware-cli invoice list --status open|overdue|paid|draft|voided
  lexware-cli invoice get <id>
  lexware-cli invoice create --contact <id> --item "Beratung" --net 800 [--finalize]
  lexware-cli invoice pdf <id> --out inv.pdf [--open]

  `list` goes through the voucherlist hub (the only list view; a status is
  required, defaults to open). `create` makes a DRAFT unless `--finalize` (which
  assigns a number and issues it — one-way). `pdf` needs a FINALIZED invoice; a
  draft returns a conflict. `--open` previews in your system viewer (no-ops headless).
""",
    "documents": """\
SALES DOCUMENTS (beyond invoices)

  Each type is its own group with the same shape — list (via voucherlist, needs a
  --status), get, create (draft unless --finalize), and PDF where it applies:

    lexware-cli quotation list --status open
    lexware-cli quotation create --contact <id> --item "Angebot" --net 5000
    lexware-cli credit-note create --contact <id> --item "Gutschrift" --net 100 --preceding <invoiceId>
    lexware-cli delivery-note create --contact <id> --item "Ware"      # no prices
    lexware-cli order-confirmation list --status open
    lexware-cli down-payment-invoice get <id>                          # read-only
    lexware-cli dunning create --contact <id> --item "Mahnung" --preceding <invoiceId>

  Notes: dunnings REQUIRE a --preceding invoice; down-payment-invoices are
  read-only; delivery-notes carry no money. All follow the draft/finalize rule.
  Bookkeeping (income/expense) entries live under `lexware-cli voucher`, and the
  product catalogue under `lexware-cli article`.
""",
    "webhooks": """\
WEBHOOKS — "tell me when things change"

  lexware-cli webhook events                       # what you can subscribe to
  lexware-cli webhook subscribe --event invoice.created --url https://you/hook
  lexware-cli webhook list
  lexware-cli webhook get <subscriptionId>
  lexware-cli webhook delete <subscriptionId>

  Register an HTTPS callback for an event (contact.changed, invoice.created,
  payment.changed, ...). Lexware POSTs the event + affected resource id to your URL
  when it fires; you then fetch the detail. Preview a subscribe with `--dry-run`.
""",
    "contacts": """\
CONTACTS (customers & vendors)

  lexware-cli contact list [--customer|--vendor] [--name Muster] [--email a@b]
  lexware-cli contact get <id>
  lexware-cli contact create --company "Muster GmbH" --role customer
  lexware-cli contact create --first-name Erika --last-name Muster --role customer

  A contact is a company XOR a person, with at least one role. `create` returns an
  action-result; the assigned customer/vendor number is fetched and included.
  Name/email filters need >=3 characters. There is no delete.
""",
    "auth": """\
AUTHENTICATION

  lexware-cli auth login              # prompts, shows where to get a key, verifies
  lexware-cli auth login --sandbox    # against api.lexware-sandbox.io
  lexware-cli auth status             # which key/backend + which organisation
  lexware-cli auth logout

  Precedence: env (LEXWARE_API_KEY) > OS keyring > 0600 file. `auth status` names
  which one is in use — an exported key silently overrides a stored login.
""",
    "pacing": """\
PACING & THE RATE LIMIT

  The API allows ~2 req/s org-wide with NO rate-limit headers. The client runs a
  token bucket and auto-delays every request to stay under the ceiling — you never
  configure it. A large `receivables` or `contact list` just takes longer.

  On a 429 (usually a SHARED budget — another integration on the same org) it
  backs the limiter off and retries with jitter. If it still fails, that's exit 8
  (rate-limited): wait and retry, it is not a hard error. Note a 429 can even
  arrive dressed as HTTP 500; the client handles that too.
""",
    "output": """\
OUTPUT

  -o json (default) | table | markdown | csv   — anywhere on the line
  --fields voucherNumber,openAmount            — trim
  --stream                                      — NDJSON
  --dry-run                                     — preview a write, exit 0

  RESERVED (never a command's own option): --format/-f, --output/-o, --fields,
  --columns, --dry-run, --stream, --no-context. File outputs are `--out`.
""",
    "gotchas": """\
GOTCHAS — all verified against the real API

  - `overdue` is derived ONLY in the invoice list (voucherlist). A single invoice
    GET reports `open`, never `overdue`. Compute aging from the due date.
  - Sum **openAmount**, not the invoice total. A partial payment reduces openAmount
    but does NOT change the status — an invoice can be overdue AND partly paid.
  - Draft vs finalized: creates are drafts; `--finalize` issues them (one-way, gets
    a number). A draft cannot be rendered to PDF (409 — finalize first).
  - POST/PUT return an action-result {id, resourceUri, ..., version}, NOT the
    object. `get` it to see the assigned number.
  - Optimistic locking: an update needs the current `version`; a stale one is a
    conflict (exit 6) — even when the API dresses it as a 406.
  - Two things the API simply does not have: PAYROLL and BANK-ACCOUNT MANAGEMENT.
    Don't look for them.
  - The client paces itself; don't add your own sleeps. See `guide pacing`.
"""
}


def guide(topic: str = typer.Argument(None, help="A topic to expand; omit for the overview.")) -> None:
    """Built-in operating guide — how to use this CLI without external docs."""
    if topic is None:
        typer.echo(OVERVIEW)
        return
    key = topic.strip().lower()
    if key in ("topics", "list"):
        typer.echo("\n".join(sorted(TOPICS)))
        return
    body = TOPICS.get(key)
    if body is None:
        typer.echo(f"No topic {topic!r}. Available:\n  " + "  ".join(sorted(TOPICS)) + "\n\nRun `lexware-cli guide` for the overview.", err=True)
        raise typer.Exit(2)
    typer.echo(body)

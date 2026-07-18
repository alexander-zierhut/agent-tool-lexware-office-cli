# lexware-office — the agent-ready Lexware Office CLI

> A fast, scriptable **Lexware Office CLI** for contacts, invoices, quotations and
> the whole German sales-document zoo — and the first Lexware command-line tool
> designed to be driven by **AI agents** (Claude, Cursor, LLM tool-loops) as well
> as humans. Its headline trick: **the receivables total and AR-aging the API
> refuses to compute for you.**

[![PyPI](https://img.shields.io/pypi/v/agent-tool-lexware-office-cli)](https://pypi.org/project/agent-tool-lexware-office-cli/)
[![CI](https://github.com/alexander-zierhut/agent-tool-lexware-office-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/alexander-zierhut/agent-tool-lexware-office-cli/actions/workflows/ci.yml)
![Python](https://img.shields.io/pypi/pyversions/agent-tool-lexware-office-cli)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Agent ready](https://img.shields.io/badge/agent-ready-8A2BE2)

**Install:** `pipx install agent-tool-lexware-office-cli` — then run `lexware-office guide`.

[**agent-tool-lexware-office-cli**](https://pypi.org/project/agent-tool-lexware-office-cli/)
(the installed command is `lexware-office`) is a Python command-line interface for
the [Lexware Office](https://www.lexware.de/lexware-office/) (formerly lexoffice)
public REST API. It covers the day-to-day billing workflow — **contacts**,
**invoices** (create, finalise, record payments, download the PDF), quotations,
order confirmations, credit notes, delivery notes, dunnings, articles, bookkeeping
vouchers and webhooks — all with first-class JSON output so it slots straight into
automation and AI agents.

### Why this Lexware Office CLI?

- 💶 **The number the API won't total.** Lexware exposes vouchers one page at a
  time and never sums what is still owed. `lexware-office receivables` walks the
  open items, totals them, and buckets them into **AR aging** (current / 30 / 60 /
  90+ days) — the single answer *"who owes us money, and how late?"* that the API
  makes you compute yourself.
- 🤖 **Agent-ready** — structured JSON on stdout, structured errors on stderr,
  stable exit codes, and a built-in **`lexware-office guide`** playbook so an agent
  can learn the tool from the tool. See [AGENTS.md](AGENTS.md).
- ⏱️ **Self-throttling under a rate limit with no headers.** The Lexware API caps
  you at **2 requests/second** and returns **no rate-limit headers** to pace
  against. The client throttles itself under the limit *and* retries the 429s that
  slip through — so a multi-page `receivables` scan just works instead of erroring
  halfway.
- 🖇️ **Four output formats** — `json` (default), `table`, `markdown`, `csv`; pick
  per command with `-o`, trim to exact `--fields`, or `--stream` NDJSON.
- 🧪 **Safe by default** — `--dry-run` previews any write at the transport layer,
  and `lexware-office context` gives sticky per-session defaults.
- 🔐 **Safe credentials** — API key in the OS keyring (Secret Service / macOS
  Keychain / Windows Credential Locker), with a `0600` file fallback.
- 🧰 **Escape hatch** — `lexware-office raw` calls any endpoint the typed commands
  don't wrap.

**Keywords:** Lexware Office CLI, lexoffice CLI, Lexware command line, Lexware API
client, invoicing automation, accounting CLI, accounts receivable, AR aging,
Rechnung, Angebot, Mahnung, AI agent tool, LLM tooling, Claude, DevOps automation.

## The command surface

Everything is discoverable from the binary — `lexware-office --help`, then
`lexware-office guide` for the playbook and `lexware-office <group> --help` for any
group. The top level:

```text
 Usage: lexware-office [OPTIONS] COMMAND [ARGS]...

 Agent-friendly CLI for Lexware Office: contacts, invoices, and the
 receivables/AR-aging the API refuses to total for you.

 Output is JSON on stdout by default (errors are JSON on stderr with a non-zero
 exit code); add `-o table` or trim with `--fields`. The client paces itself under
 the 2 req/s limit automatically.

 New here? Run `lexware-office guide`.  Start with `lexware-office receivables` to
 see who owes you money.

╭─ Commands ───────────────────────────────────────────────────────────────────────╮
│ guide                 Built-in operating guide — how to use this CLI.            │
│ receivables           Outstanding receivables + AR aging — the number the API   │
│                       won't total.                                              │
│ contact               Customers & vendors: list, get, create, update.           │
│ invoice               Invoices: list, get, create, finalize, payments, PDF.     │
│ quotation             Quotations (Angebote): list, get, create, PDF.            │
│ order-confirmation    Order confirmations (Auftragsbestätigungen).              │
│ credit-note           Credit notes (Gutschriften).                              │
│ delivery-note         Delivery notes (Lieferscheine).                           │
│ down-payment-invoice  Down-payment invoices (read-only).                        │
│ dunning               Dunnings (Mahnungen) — require a preceding invoice.       │
│ article               Articles: products & services catalogue.                  │
│ voucher               Bookkeeping vouchers (accounting entries).                │
│ webhook               Webhooks: subscribe to events, list, delete.              │
│ reference             Reference data: countries, categories, payment conditions.│
│ recurring             Recurring invoice templates (read-only).                  │
│ file                  Download stored files by id.                              │
│ auth                  Log in, log out, inspect credentials.                     │
│ profile               The connected organisation — and what your key can do.    │
│ raw                   Escape hatch: call any API path directly.                 │
│ settings              View & change CLI settings.                               │
│ context               Sticky session defaults, per profile.                     │
│ install               Integrate with other tools (e.g. `install claude`).       │
╰──────────────────────────────────────────────────────────────────────────────────╯
```

Global options — `-o/--output json|table|markdown|csv`, `--fields`, `--dry-run`,
`--stream`, `--no-context` — are stripped from argv before parsing, so they work
anywhere on the line. Full reference: [docs/COMMANDS.md](docs/COMMANDS.md).

## Quick start

### 1. Install

```bash
pipx install agent-tool-lexware-office-cli      # isolated, puts lexware-office on PATH
# or: pip install agent-tool-lexware-office-cli
# or, from a clone: python3 -m venv .venv && . .venv/bin/activate && pip install -e .
```

### 2. Log in

```bash
lexware-office auth login       # asks for your API key, then verifies it
lexware-office profile          # the connected organisation + what your key can do
```

Create an API key in the Lexware Office web app under **Einstellungen →
Öffentliche API**. `login` verifies the key before persisting anything, saves the
connection profile, and stores the key in your keyring. For headless/CI use:

```bash
export LEXWAREOFFICE_TOKEN=xxxxxxxx
lexware-office receivables
```

### 3. Use with Claude Code

```bash
lexware-office install claude          # writes a Claude Code skill
lexware-office install claude --print  # preview it first
```

The skill points Claude at `lexware-office guide`, so it learns the tool from the
tool.

## Command highlights

Run `lexware-office <group> --help` for full options, or `lexware-office guide <topic>`.

```bash
lexware-office receivables                         # who owes money, totalled + aged
lexware-office receivables -o table --fields voucherNumber,openAmount,daysOverdue

lexware-office contact ls --query "Muster"         # find a customer
lexware-office invoice create --contact <id> ...   # draft an invoice
lexware-office invoice finalize <id>               # draft -> issued (irreversible)
lexware-office invoice pdf <id> --out invoice.pdf  # binary carve-out: writes a file
lexware-office invoice payment <id> --amount 119.00

lexware-office invoice create --contact <id> --dry-run   # preview the request, send nothing
lexware-office raw get contacts?page=0                    # escape hatch
```

## Output for agents

- Default output is JSON on **stdout**. Errors are JSON on **stderr** with a
  non-zero exit code (`{"error": "...", "status": 404}`).
- **Exception:** PDF downloads (`invoice pdf`, `voucher`/`file` downloads) write
  **binary** to a file — they are not JSON, so don't `json.loads` them.
- Exit codes follow the family contract: `0` ok · `1` generic · `3` config ·
  `4` auth · `5` not-found · `6` conflict · `7` validation · `8` rate-limited · `130` interrupted.
- The client self-throttles under Lexware's undocumented 2 req/s limit and retries
  429s, so paged scans complete without special handling.

Full contract: [AGENTS.md](AGENTS.md).

## Contributing / Development

**You do not need a Lexware account or an API key to contribute.** Clone it and run:

```bash
pip install -e '.[test]'
pytest                    # hermetic tests are green on a clean checkout, no account
```

The integration tests boot the sibling
**[lexware-office-api-mock](https://github.com/alexander-zierhut/lexware-office-api-mock)**
as their backend — there is no local Lexware test instance, so the mock (built from
verbatim API responses captured during research) is the substitute. Point the suite
at the mock or a real sandbox with `LEXWAREOFFICE_BASE_URL`; without it, the
integration tier skips itself. See [BUILDING.md](BUILDING.md) for the full build
and release playbook.

## Part of the family

Built on **[agent-tool-shared-cli](https://github.com/alexander-zierhut/agent-tool-shared-cli)** —
the chassis every tool in this family shares: JSON on stdout, JSON errors on
stderr, a stable cross-tool exit-code contract, `--dry-run`, four output formats,
and a built-in `guide` so an agent can learn each tool from the tool itself.

| Tool | Install | For |
| --- | --- | --- |
| [**drone-cli**](https://github.com/alexander-zierhut/agent-tool-drone-cli) | `pipx install agent-tool-drone-cli` | Drone CI — builds, failing-step logs, promotions |
| [**grafana-cli**](https://github.com/alexander-zierhut/agent-tool-grafana-cli) | `pipx install agent-tool-grafana-cli` | Grafana — log discovery, health scan, alert routing |
| [**openproject**](https://github.com/alexander-zierhut/agent-tool-openproject-cli) | `pipx install agent-tool-openproject-cli` | OpenProject — work packages, time, invoicing |
| [**lexware-office**](https://github.com/alexander-zierhut/agent-tool-lexware-office-cli) | `pipx install agent-tool-lexware-office-cli` | Lexware Office — invoices, contacts, AR-aging |

They compose over the shared contract:
`openproject time report --month 2026-07 && lexware-office invoice create ...`
turns tracked hours into an invoice.

## License

MIT — see [LICENSE](LICENSE).

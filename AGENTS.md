# Using `lexware-office` from an AI agent

The **machine contract** for driving this CLI. For the human tutorial see the
[README](README.md); for every option see [docs/COMMANDS.md](docs/COMMANDS.md).

> **No context? Start here:** run **`lexware-office guide`**. The CLI ships its own
> playbook (output contract, auth, the domain model, verified gotchas) so you can
> bootstrap from the binary alone, with no external docs and no network. Then
> `lexware-office guide <topic>`.

## The output contract

- **stdout is JSON.** Parse it. Success exits `0`.
- **Errors are JSON on stderr**, non-zero exit: `{"error": "...", "status": 404}`.
- **The one exception: PDF/file downloads print BINARY**, not JSON — `invoice pdf`,
  `voucher`/`file` downloads write bytes to a file (`--out`). Never `json.loads`
  a PDF.
- **Exit codes** are stable, published API — branch on them:

  | Code | Meaning |
  | --- | --- |
  | 0 | success (including a successful `--dry-run`) |
  | 1 | generic error |
  | 3 | config (no profile / bad config) |
  | 4 | auth (401/403 — key missing or wrong) |
  | 5 | not found (404) |
  | 6 | conflict (409) |
  | 7 | validation (400/406 — see the error body) |
  | 8 | rate-limited: the client's own pacing **and** its retry budget were both exhausted (usually a *shared* org budget, since our pacing alone will not 429) |
  | 130 | interrupted (SIGINT) |

  `2` is Click/Typer usage error — never allocated. Codes `0–7` mean the same
  across the whole tool family; `8` is this tool's own.

## Run it non-interactively

```bash
export LEXWAREOFFICE_TOKEN=xxxxxxxx
lexware-office receivables
```

The env key wins over the keyring. The CLI never prompts unless **stdin and stdout
are both TTYs**, so a pipeline can never be blocked by a question.

## The premise: the API won't total your receivables — this does

Lexware returns vouchers one page at a time and never sums what is still owed.
`lexware-office receivables` walks the open items under the rate limit, totals
them, and buckets them into AR aging.

```bash
lexware-office receivables                                   # totalled + aged
lexware-office receivables --fields voucherNumber,openAmount,daysOverdue -o table
```

## The rate limit is the thing to understand

The Lexware API allows ~**2 requests/second org-wide** and sends **no rate-limit
headers**. Correctness means not over-emitting:

- Every request goes through a **blocking token bucket** — one request per
  interval, no bursts. You do not need to sleep between calls; the client does it.
- **A 429 can arrive as HTTP 500** (`"...or rate limit exceeded"`) and is treated
  as a retryable rate-limit, not a hard failure.
- **A 504 may have already succeeded** — the client never blind-retries a POST, so
  you will not double-create an invoice.
- If you still hit exit `8`, something else is spending the same org's budget. Back
  off and try later; it is not a hard failure.

## Spend fewer tokens

- **`--fields`** trims the payload: `--fields voucherNumber,openAmount`.
- **`--stream`** emits NDJSON, one object per line.
- **`-o csv` / `-o table` / `-o markdown`** when JSON isn't the right shape.

These **globals** work **anywhere on the line** — before or after the subcommand:
`--output`/`-o`, `--format`/`-f`, `--fields`/`--columns`, `--dry-run`, `--stream`
and `--no-context`. They're stripped from argv before parsing, so no command may
declare one of those names as its own option.

## Preview writes

Add **`--dry-run`** to any mutating command. It is intercepted in the transport, so
every write gets it and none can bypass it.

```bash
lexware-office invoice create --contact <id> --dry-run
# -> {"dryRun": true, "request": {"method": "POST", "url": "...", ...}}
```

## Gotchas worth knowing

- **`invoice finalize` is irreversible** — a finalised (issued) invoice cannot go
  back to draft. Preview with `--dry-run` first.
- **Dunnings require a preceding invoice**; down-payment invoices and recurring
  templates are **read-only** over the API.
- **Money is decimal.** Amounts are strings/decimals in the API — do not coerce
  through float.
- **German document types** map to the API's English resource names: Angebot =
  `quotation`, Auftragsbestätigung = `order-confirmation`, Gutschrift =
  `credit-note`, Lieferschein = `delivery-note`, Mahnung = `dunning`.

Use `--profile/-p <name>` to target a specific organisation when several keys are
configured.

## Reporting a problem — open a GitHub issue

If a task was painful, needed too many steps, hit a missing feature, or was
impossible with `lexware-office` — **and the user asks you to file it** — open an issue on
this tool's own repo. Only when asked; never unprompted; one issue per problem.

- Repo: `alexander-zierhut/agent-tool-lexware-office-cli`
- Issues: https://github.com/alexander-zierhut/agent-tool-lexware-office-cli/issues
- Self-contained (no repo/README needed beside the binary): `lexware-office report` prints exactly this — the repo, a pre-filled `issues/new` link, and a `gh` one-liner — offline, no token.

Search for a duplicate first, then file — prefer the `gh` CLI:

```bash
gh issue list   --repo alexander-zierhut/agent-tool-lexware-office-cli --search "<keywords>"
gh issue create --repo alexander-zierhut/agent-tool-lexware-office-cli \
  --title "<one-line summary>" \
  --body  "<goal · exact command(s) run · JSON error + exit code · `lexware-office --version` · what would have made it work>"
```

If `gh` is missing or unauthenticated, hand the user a prefilled link instead:
`https://github.com/alexander-zierhut/agent-tool-lexware-office-cli/issues/new?title=…&body=…`.

# Building the Lexware Office CLI — the playbook, distilled from four tools

This is the handoff document for building `lexware-cli` (working name), the fourth
tool in the `agent-tool-<x>-cli` family after **openproject**, **drone**, and
**grafana**. Read this first, then `spike/API_MAP.md` and
`spike/RESPONSE_EXAMPLES.md` (the verbatim API responses captured while we still
had the research window — **there is no local test instance for Lexware, so those
examples are the substitute for one**).

The full family standard is `../_shared/BLUEPRINT.md` (946 lines). The three
reference implementations are the real teachers — read the freshest, `grafana/`,
and copy its shape:
- `/workspace/Development/zierhut-it/agent-tools/grafana/`  (closest sibling; richest tests)
- `/workspace/Development/zierhut-it/agent-tools/drone/`
- `/workspace/Development/zierhut-it/agent-tools/openproject/`

---

## 0. What these tools are (the contract that never changes)

An agent-ready CLI: a thin, honest wrapper over one product's API, built to be
driven by an LLM with no context beyond the binary itself.

- **stdout is JSON. Always.** Errors are JSON on **stderr** with a **non-zero exit
  code**: `{"error": "...", "status": 404}`. The one carve-out is a command that
  emits inherently-textual payload (drone's `log view`, grafana's `logs query
  --raw`) — document it on the guide's first screen. For Lexware the analog is a
  **binary carve-out**: `voucher`/`invoice` PDF download writes a file, it is not JSON.
- **Exit codes are published API across the whole family:** `0` ok (incl. a
  successful `--dry-run`) · `1` generic · `2` **reserved for Click/Typer, never
  allocate** · `3` config · `4` auth · `5` not-found · `6` conflict · `7`
  validation · `130` SIGINT. Extend from **8 upward**, only for a condition you
  have OBSERVED. 0–7 mean the same thing in every tool; 8+ are the tool's own.
- **`--dry-run`** previews any write without sending it (intercepted in the
  transport, so no command can bypass it).
- **`-o table|markdown|csv`**, **`--fields a,b`**, **`--stream`** (NDJSON) work
  anywhere on the line.
- **A built-in `guide`** that works with **no config, no token, no network** —
  it is what an agent runs first and what a human runs when everything is broken.
- **`install claude`** writes a SKILL.md so Claude reaches for the tool by name.
- **Findings are not failures.** "This invoice is overdue" is an observation the
  CLI *succeeded* at making → exit 0. Gate a non-zero exit behind an explicit
  `--exit-code`, in a band far from the error codes (20+).

---

## 1. The shared chassis (`agent-tool-shared-cli`, import `agentcli`)

On PyPI at **0.1.2** (bump the floor to `>=0.1.2` — see the columns scar below).

```python
from agentcli import (
    AppSpec, Credentials,          # identity + token storage
    Emitter, OutputFormat,         # ALL output goes through this
    print_error,
    OpError, ApiError, AuthError, ConfigError,
    ConflictError, NotFoundError, ValidationError, DryRun,
)
```

### `AppSpec` — the only tool-specific part of the chassis
```python
SPEC = AppSpec(
    name="lexware-cli",                 # -> ~/.config/lexware-cli/ + keyring service
    env_prefix="LEXWARECLI",            # -> LEXWARECLI_TOKEN, LEXWARECLI_CONFIG_DIR, ...
    token_env_aliases=("LEXWARE_API_KEY", "LEXOFFICE_API_KEY"),  # ecosystem names, honoured AFTER ours
)
SPEC.config_dir()      # FUNCTION, not a constant — this is what makes tests hermetic
SPEC.config_file()     # ~/.config/lexware-cli/config.json
SPEC.token_env_names() # -> ("LEXWARECLI_TOKEN", "LEXWARE_API_KEY", "LEXOFFICE_API_KEY")
```
`token_env_aliases` is the seam that already earned its keep twice (drone's
`DRONE_TOKEN`, grafana's `GRAFANA_TOKEN`). Lexware's SDKs read `LEXWARE_API_KEY` /
the older `LEXOFFICE_API_KEY`; honour both, after ours.

### `Credentials`
Precedence is **env > keyring > 0600 file** and MUST NOT be inverted (CI depends
on it). Because an exported `LEXWARE_API_KEY` therefore silently overrides a
keyring login, `auth status` must always **name the backend in use**
(`credentials.backend_name()`). Visibility, never inversion.

### `Emitter` — every payload, no exceptions
```python
obj.emitter.emit(data, columns=["id", "name", "roles"])   # json|table|markdown|csv + --fields
obj.emitter.stream_json(iterable)                          # NDJSON
obj.emitter.message("human note")                          # TABLE MODE ONLY — allowlisted
```
Never `print()` a payload. Never build JSON by hand. **Columns accept bare
strings OR `(header, accessor)` tuples** as of shared 0.1.2 — either is fine.

---

## 2. Module layout (copy from `grafana/src/grafanacli/`)

```
src/lexwarecli/
  __init__.py      __version__ = "0.1.0"   <- THE SINGLE SOURCE (see the release scar)
  __main__.py      `python -m lexwarecli`  <- REQUIRED; the test harness shells it
  spec.py          SPEC = AppSpec(...) + credentials instance + token_url(server)
  errors.py        re-export the shared taxonomy + Lexware-specific codes (8+)
  config.py        Profile/Config, settings, env precedence
  appctx.py        AppContext: the DI container. NOT context.py (that is sticky-defaults)
  client.py        httpx wrapper: auth, retry (429!), pagination, dry-run, error mapping, optimistic locking
  <domain>.py      pure logic — the testable heart (e.g. money.py, receivables.py)
  commands/
    _shared.py     ctx_obj(), need_*() resolvers
    guide.py       the built-in manual  <- NON-NEGOTIABLE
    auth.py settings.py context.py install.py raw.py
    <domain groups: contact, invoice, quotation, voucher, ...>
```

**pyproject MUST read the version dynamically** — this is a real scar, not a
style choice:
```toml
[project]
dynamic = ["version"]
[tool.setuptools.dynamic]
version = { attr = "lexwarecli.__version__" }
```
(OpenProject shipped a STATIC `version = "0.4.1"` in pyproject while the bump only
touched `__init__.py`; the build produced a stale-versioned wheel, PyPI rejected
it as "File already exists" AFTER the tag and GitHub release were cut. One source
of truth or it drifts.)

---

## 3. The reserved global namespace — get this right FIRST

`cli.py::_pop_globals` strips these from **anywhere** on the line, before Click
parses:
```python
_FORMAT_FLAGS = ("--format", "-f", "--output", "-o")
_FIELDS_FLAGS = ("--fields", "--columns")
_BOOL_FLAGS   = ("--dry-run", "--stream", "--no-context")
```
**No command may declare an option with those names** — it could never receive
one. Copy `grafana/tests/test_globals_unit.py`; it walks the whole tree and fails
on a collision. **Reserve ONLY the popped flags** — `--version/-V`,
`--profile/-p`, `--no-color` are ordinary root options a subcommand may shadow.

For Lexware the obvious trap is a **file destination**: PDF/download commands must
spell it `--out PATH`, never `--output`. (`attach download --output f.pdf` wrote
to the CWD silently, exit 0, in OpenProject for four releases.)

---

## 4. The command surface every tool ships

- **`guide`** — the built-in manual. Verify it survives a bare environment:
  `env -i PATH=/usr/bin:/bin HOME=/nonexistent ./lexware-cli guide` → exit 0.
  Structure: OVERVIEW (what it is · output contract · exit codes · auth · THE key
  concept · gotchas · discover · TOPICS list) + `TOPICS: dict[str,str]` **including
  a `gotchas` topic** (an agent reaches for that name first). A test resolves every
  command the guide/SKILL name against the real tree — docs that name a nonexistent
  command are a shipped bug (drone did it twice).
- **`auth login`** — interactive: get the key at
  `https://app.lexware.de/addons/public-api`; **verify the key before persisting**
  (`GET /v1/profile`), and store the organization name/id it returns.
- **`auth status`** — names WHICH token/backend is in use.
- **`settings`** — every setting has a sane default or is asked once on first run.
- **`context`** — sticky defaults (e.g. a default `contact`), keyed appropriately.
- **`install claude`** — anchor every trigger word to the product noun
  ("Lexware Office", "a Lexware invoice", "a customer contact"); bare
  "invoice"/"contact" over-fires.
- **`raw`** — the escape hatch: call any API path directly.
- **`server doctor` / `profile`** — chain the reachability/identity/permission
  probes. **Doctor must never raise; returning the report IS its job.** End every
  probe ladder in `except OpError` (NotFoundError and ApiError are SIBLINGS, so an
  `except ApiError` ladder looks exhaustive and is not — it leaked a raw error out
  of drone's doctor).

---

## 5. Lexware-specific decisions (fill in from the spike, but the shape is known)

- **Command name: `lexware-cli`** (matches the family: `drone-cli`, `openproject`).
  There is no official `lexware-cli` binary to collide with (unlike grafana), so
  this one is uncontested. Dist: `agent-tool-lexware-cli`.
- **Auth is a single API key** — simpler than the others. No basic auth, no OAuth
  dance for the public API. `Authorization: Bearer <key>`.
- **Rate limit is REAL and low: 2 req/sec → HTTP 429 — the client MUST rate-limit
  AND retry. Non-negotiable, and confirmed live** (a burst earned an instant 429;
  pacing at ~1.4/s ran clean). This is stricter than any sibling — grafana retried
  429 but never had to *pace* itself. The full spec is `spike/LIVE_FINDINGS.md §0`;
  in short, `client.py` needs **both**:
    1. **Proactive token bucket** — target ≤ ~1.5 req/s and gate *every* request
       through it (there are **no `X-RateLimit`/`Retry-After` headers**, so you
       cannot react your way to correctness — you must not over-emit). Each page of
       a sweep counts; the AR-aging fan-out inherits this by routing through the one
       client.
    2. **Reactive backoff** — on 429, exponential backoff + jitter, capped attempts.
       Encode two live subtleties: a **429 can masquerade as HTTP 500** (body
       *"Internal server error or rate limit exceeded"*) → retryable; and a **504
       may have SUCCEEDED** → do NOT blind-retry a non-idempotent POST (verify with
       a GET first, or you double-create an invoice).
  The paced `request()` in the spike is the working prototype — port its shape.
- **Optimistic locking via `version`** — like OpenProject's `lockVersion`. Every
  PUT needs the current `version`; a stale one is a conflict (exit 6). The
  read-modify-write pattern (fetch, mutate, PUT the whole body back) is the same
  one grafana's `alert pause` uses. DO the fetch even under `--dry-run` (reads
  execute; only writes are intercepted) so the printed request is real.
- **Pagination is the Spring "Pageable" wrapper** (`content`/`totalPages`/
  `totalElements`/`number`/`size`/`first`/`last`). This has an authoritative
  `totalPages`, so the stop rule is **OpenProject's, not drone's**: page until
  `last == true` (or `number+1 >= totalPages`); a short `content` array is NOT the
  end. Copying drone's "short page = done" rule would truncate. (This is exactly
  why the transport is NOT shared across tools — each API's pagination inverts.)
- **The draft-vs-finalized lifecycle** for sales documents is the big semantic
  trap. Invoices/quotations/etc. exist as *drafts* (editable, not legally issued)
  and *finalized* (immutable, numbered, renderable to PDF). A CLI that lists
  "invoices" without distinguishing is lying. The `voucherStatus` enum
  (draft/open/paid/voided/overdue — confirm exact values in the spike) is the
  discriminator, and the `voucherlist` endpoint + its filters are how you query by
  it. `--dry-run` and clear status reporting matter here.
- **Money and tax.** Amounts are gross/net with tax broken out; get the field
  semantics exactly right from the examples (a wrong gross/net assumption is a
  silent, invisible-to-tests financial error). Put money handling in a pure
  `money.py` with tests. Never do float math on currency — the API uses decimals;
  parse and carry them as such.
- **PDF download + immediate preview — a user-requested feature (flow verified
  live, `spike/LIVE_FINDINGS.md §3b`).** `GET /v1/invoices/{id}/file` (Accept `*/*`)
  returns the PDF directly in one call (the `/document`→`{documentFileId}`→`/files/{id}`
  two-step is a fallback). Build it as:
    - **`invoice pdf <id> --out PATH [--open]`** — download any finalized invoice's PDF.
    - **`invoice create ... --pdf [PATH] [--open]`** — after create, chain the download.
    Rules that keep it inside the agent contract:
    - The PDF is the **binary carve-out**: it is written to a file (`--out`/`--pdf`,
      **never `--output`** — reserved), and the JSON on stdout reports the path
      (`{"pdf": "…/RE1234.pdf", "opened": true}`). Never write binary to stdout.
    - **`--open` is an opt-in HUMAN affordance** (system viewer: `xdg-open`/`open`/
      `start`). Default OFF — an agent must not trigger a GUI. In a headless/CI
      context (no `DISPLAY`, `CI=true`) it **no-ops gracefully** and says so in the
      JSON, never failing the command.
    - **A draft cannot be rendered → `409`.** Do NOT auto-finalize (finalizing is
      one-way and legally significant); surface a clear "finalize first" error (exit 6).

### The killer feature — derive the number the API refuses to give
Per the family principle (`[[agent-tool-killer-feature-principle]]`): the Lexware
API answers *per-invoice* status but refuses the *aggregate* questions a business
actually asks. Strong candidates (the spike's "refused questions" section will
confirm which are real):
- **Outstanding receivables / AR aging** — "who owes me money, and how overdue?"
  Sum open invoices per contact into 0-30/31-60/61-90/90+ buckets. The API gives
  each invoice's status + dueDate + open amount and never totals them.
- **Revenue for a period** — sum finalized invoices over a date range (no
  reporting endpoint).
- **Quote→invoice conversion** — which quotations never became invoices.
- **Duplicate contact detection** — the contacts API has no dedup; derive it from
  name/email/vatId collisions.
Pick ONE as the headline and build it early — it is the product, not a nice-to-have.

---

## 6. Testing — the rule that shaped grafana, adapted to "no test instance"

**Test against your own thing, never against someone's production.** For the other
three we booted a Docker stack. **Lexware Office has no self-hostable instance** —
this is the defining constraint of this build. So:

1. **Hermetic tier (the bulk):** a hand-rolled fake client (NOT httpx MockTransport
   — a transport mock tempts you into simulating the API, and the API is wrong in
   ways you would encode wrongly). Feed it the **verbatim response examples from
   `spike/RESPONSE_EXAMPLES.md`** as canned responses. This is why capturing them
   now matters: they are the fixtures the whole hermetic suite runs against, and
   they came from the real docs, so they are honest.
2. **Contract tests on the pure logic** — money, receivables/aging, pagination
   stop-rule, the draft/finalized discriminator, LogQL-equivalent query building.
   These need no server at all.
3. **Live tier (opt-in, gated):** the user has a real Lexware Office account. Guard
   live tests behind `LEXWARE_API_KEY` presence → **skip, not fail**, when absent.
   **READ-ONLY by construction** against a real account (it is real accounting
   data). If any write test is ever added, gate it behind an explicit
   `LEXWARE_ALLOW_WRITES=1` interlock that only a throwaway/sandbox context sets,
   and add the meta-test that asserts the interlock is armed (it caught a real bug
   in grafana). Prefer the **sandbox/test organization** Lexware offers, if any —
   confirm in the spike.
4. `conftest.py`: snapshot the environment BEFORE the autouse hermetic fixture
   strips it (grafana's `live_env`), or live tests read an already-emptied
   `os.environ`. The hermetic fixture must strip every `LEXWARE*`/`LEXOFFICE*` var.
5. `make test-unit` = `pytest -m "not integration"` — **the marker, never a file
   list** (OpenProject ran 30 of 144 while claiming all).

**The contributor promise, stated FIRST in the README:** `pip install -e '.[test]'
&& pytest` is green on a clean checkout — no account, no key, no network, ~2s.

---

## 7. Release process (every scar folded in)

- **Dynamic version** (§2) — the single source of truth.
- **Release workflow guard:** read the version off the BUILT WHEEL and fail loudly
  if it differs from the tag, BEFORE upload (`BUILT=$(basename dist/*.whl | cut -d- -f2)`;
  compare to `${GITHUB_REF_NAME#v}`). Plus `skip-existing: true` so a binary re-run
  can't redden a good publish. (Both are in grafana/drone's release.yml; copy them.)
- **The version guard job reads the wheel, does NOT `import` the package** — the
  release job installs only `build`, so an import dies on httpx/rich. (Cost the
  shared repo a release once.)
- **Publish shared-lib bumps BEFORE dependent tools**, and expect PyPI's simple
  index to lag its JSON API by minutes — a downstream CI that pins a
  just-published floor can fail on propagation lag; a re-run fixes it.
- PyPI Trusted Publishing (OIDC), `environment: pypi`. PyInstaller onefile binaries
  named `lexware-cli-<platform>`, attached independently so a slow runner never
  blocks the publish.

---

## 8. Build order (proven four times)

0. **Spike first — DONE for the API surface** (see `spike/`). The equivalent of a
   live probe here is capturing verbatim responses, because there is no instance to
   probe repeatedly. If the user grants an API key, do a ONE-TIME read-only live
   pass to confirm the captured shapes still hold (the docs have been wrong before
   in every tool).
1. Chassis: `spec/errors/config/client/appctx/cli` + `__main__.py`. Reserved-flag
   test immediately. Get the **429 retry** and the **Pageable stop-rule** right in
   `client.py` from the start.
2. Pure logic + hermetic tests fed by the captured examples: `money.py`,
   `receivables.py` (the killer feature), the pagination iterator, the
   draft/finalized helpers.
3. The killer feature early — it is the product.
4. Read surface (contacts, invoices, vouchers, voucherlist), then write surface
   (`--dry-run` from day one; optimistic-locking read-modify-write).
5. `guide` + `install claude` + docs + CI.
6. **Wire every group into `cli.py` and verify each resolves** (drone shipped 5
   groups never registered; one missing import reddened the whole suite).
7. Regenerate docs, run the full suite, one live read-only confirmation pass, tag.

**Fan out with agents for the bulk command modules** (worked well for grafana: an
implementer per group + adversarial review), but **the orchestrator owns `cli.py`,
the chassis, and the review.** Give each agent the reference module, the
conventions, the captured examples, and explicit file ownership.

---

## 9. Hard-won rules worth re-reading before you start

- **Reasoning is not observation** — and a written-down finding outranks nothing.
  Across the four tools, live checks disproved multiple confident claims that had
  survived a spike, a review, and six agents (grafana's "listing datasources needs
  Admin" was FALSE; the Loki timestamp note was FALSE; the level label name was
  version-dependent). For Lexware, the captured examples ARE the observation — but
  confirm against a live key once if you can.
- **Never state a count you have not counted**; name the basis.
- **`.gitignore` before the first secret-adjacent file.** The key is real money
  access — treat `.env` / any captured live response with the same care as
  grafana's infra: gitignored, scrubbed of real org data before anything is
  committed. **Never commit a real API key, organizationId, customer name, or
  address.** The captured examples in `spike/` use the DOCS' sample data (already
  synthetic) — keep it that way; if you do a live pass, scrub before saving.
- **Don't leak observed status into the exit code.** "The invoice is overdue" ≠
  "the CLI failed."
- **Money is never a float.** Decimals, carried exactly.
- **Bash: `UID` is readonly** (=1000). Use another name.
- Generated `.py` files: `write_text(..., encoding="utf-8")` + ASCII content, or
  Windows dies.
- A doc that names a command is tested against the real tree.

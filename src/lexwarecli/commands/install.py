"""`lexware-cli install claude` — register this CLI with Claude Code as a Skill.

Machinery is verbatim from the sibling CLIs (same function names — `appctx.py`'s
first-run offer calls them by name). What's fresh is `SKILL_MD`: every trigger is
anchored to "Lexware Office" or a Lexware-specific noun ("a Lexware invoice", "a
customer contact"), and only commands that exist are named.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from .. import __version__
from ..errors import OpError
from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)

SKILL_NAME = "lexware-office"
_MEM_START = "<!-- lexware-cli:start -->"
_MEM_END = "<!-- lexware-cli:end -->"

SKILL_MD = f"""\
---
name: lexware-office
description: >-
  Work with Lexware Office (lexoffice) via the `lexware-cli` command — see
  outstanding receivables and AR aging for Lexware Office invoices (who owes
  money and how overdue), list and read Lexware Office invoices, create a
  Lexware Office invoice and download its PDF, list Lexware Office customers and
  vendors, create a Lexware Office contact, and inspect the connected Lexware
  Office organisation. Use this whenever the user mentions Lexware Office,
  lexoffice, a Lexware invoice, a customer/vendor contact, or wants to know
  their outstanding receivables / overdue invoices.
---

# Lexware Office CLI (agent-tool-lexware-cli v{__version__})

The `lexware-cli` command is installed on this machine and talks to the user's
Lexware Office account over its REST API.

## Start here: the number the API refuses to total

Lexware answers per-invoice and will not aggregate. `lexware-cli receivables`
derives it: total outstanding, the 0-30/31-60/61-90/90+ aging ladder, a
per-customer rollup (`--view customers`), and who to chase (`--view dunning`).

    lexware-cli receivables
    lexware-cli receivables --view dunning
    lexware-cli invoice list --status overdue

## Commands
- `lexware-cli guide` — the built-in manual, with its own topic list.
- `lexware-cli receivables [--view aging|customers|dunning]` — the killer feature.
- `lexware-cli invoice list|get|create|pdf` — `list` needs a --status (default open);
  `pdf` needs a FINALIZED invoice; `create` makes a draft unless --finalize.
- `lexware-cli contact list|get|create` — customers & vendors.
- `lexware-cli profile show|doctor` — the connected organisation + a health check.
- `lexware-cli auth login|status|logout` — `login --sandbox` for the test API.
- `lexware-cli raw get|post|put|delete <path>` — escape hatch (paths relative to /v1).
- `lexware-cli settings`, `lexware-cli context`, `lexware-cli install claude`.

## Output contract
- Default output is JSON on stdout — parse it.
- Exception: `lexware-cli invoice pdf` writes a PDF FILE; the JSON reports its path.
- Errors are JSON on stderr with a non-zero exit code.
- Trim with `--fields voucherNumber,openAmount`; `-o table` for humans; `-o csv`.

## Exit codes
`0` ok · `1` generic · `3` config · `4` auth · `5` not found · `6` conflict ·
`7` validation · `8` rate-limited (the 2 req/s budget, usually shared — wait and
retry) · `130` interrupted.

## The client paces itself
The API allows ~2 req/s org-wide with no rate-limit headers; the client
auto-delays every request to stay under it. A big `receivables` sweep just takes
longer — never add your own sleeps.

## Auth
    lexware-cli auth login             # prompts, shows where to get a key, verifies
    lexware-cli auth login --sandbox   # api.lexware-sandbox.io
If not configured, ask the user to run `lexware-cli auth login` (or set
LEXWARE_API_KEY, + LEXWARE_URL for the sandbox). `lexware-cli auth status` names
which key/backend is actually in use.

## Make changes safely
Preview ANY write with a global `--dry-run`. Finalizing an invoice is ONE-WAY
(it issues a legal document) — confirm with the user first.

## Gotchas that bite once
- `overdue` exists ONLY in the invoice list; a single invoice GET says `open`.
  Aging is computed from the due date, not read from a status.
- Sum openAmount, not the total — a partial payment leaves an invoice overdue.
- A draft invoice cannot be turned into a PDF (finalize it first).
- Create returns an action-result {{id, ...}}, not the object — `get` it to see
  the assigned customer/vendor number.
- The API has NO payroll and NO bank-account management. Don't look for them.
"""

_MEMORY_HINT = (
    f"{_MEM_START}\n"
    "The `lexware-cli` CLI (package agent-tool-lexware-cli) is installed — an "
    "agent-ready Lexware Office client with JSON output. `lexware-cli receivables` "
    "shows who owes money + AR aging. Run `lexware-cli guide` to learn it.\n"
    f"{_MEM_END}\n"
)


def claude_available() -> bool:
    if shutil.which("claude"):
        return True
    home = Path.home()
    return (home / ".claude").is_dir() or (home / ".local" / "bin" / "claude").exists()


def _skill_dir(project: bool) -> Path:
    base = Path.cwd() if project else Path.home()
    return base / ".claude" / "skills" / SKILL_NAME


def skill_installed(project: bool = False) -> bool:
    return (_skill_dir(project) / "SKILL.md").exists()


def write_skill(project: bool = False) -> Path:
    d = _skill_dir(project)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "SKILL.md"
    path.write_text(SKILL_MD, encoding="utf-8")
    return path


def _memory_file() -> Path:
    return Path.home() / ".claude" / "CLAUDE.md"


def write_memory_hint() -> Path:
    path = _memory_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if _MEM_START in existing:
        return path
    sep = "" if existing.endswith("\n") or not existing else "\n"
    path.write_text(existing + sep + "\n" + _MEMORY_HINT, encoding="utf-8")
    return path


def _remove_memory_hint() -> bool:
    path = _memory_file()
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if _MEM_START not in text or _MEM_END not in text:
        return False
    before, _, rest = text.partition(_MEM_START)
    _, _, after = rest.partition(_MEM_END)
    path.write_text((before.rstrip("\n") + "\n" + after.lstrip("\n")).strip("\n") + "\n", encoding="utf-8")
    return True


@app.command()
def claude(
    ctx: typer.Context,
    project: bool = typer.Option(False, "--project", help="Install into ./.claude instead of ~/.claude."),
    memory: bool = typer.Option(False, "--memory", help="Also add a one-line hint to ~/.claude/CLAUDE.md."),
    force: bool = typer.Option(False, "--force", help="Install even if Claude Code isn't detected."),
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove the skill (and memory hint)."),
    print_: bool = typer.Option(False, "--print", help="Print the SKILL.md that would be written and exit."),
) -> None:
    """Register `lexware-cli` with Claude Code as a Skill. Reversible with --uninstall."""
    obj = ctx_obj(ctx)
    if print_:
        typer.echo(SKILL_MD)
        return
    if uninstall:
        d = _skill_dir(project)
        removed = []
        if (d / "SKILL.md").exists():
            (d / "SKILL.md").unlink()
            try:
                d.rmdir()
            except OSError:
                pass
            removed.append(str(d))
        if _remove_memory_hint():
            removed.append(str(_memory_file()) + " (hint)")
        obj.emitter.emit({"status": "uninstalled", "removed": removed})
        return
    if not force and not claude_available():
        raise OpError(
            "Claude Code was not detected. Install it from https://claude.com/claude-code, "
            "or re-run with --force."
        )
    skill_path = write_skill(project)
    result = {"status": "installed", "skill": str(skill_path), "scope": "project" if project else "user"}
    if memory:
        result["memoryHint"] = str(write_memory_hint())
    obj.emitter.emit(result)

#!/usr/bin/env python3
"""Generate docs/COMMANDS.md — every command and option, by introspecting the
actual Typer/Click app so the docs cannot drift from the code.

Usage:  python scripts/gen_docs.py

CI runs this and then `git diff --exit-code docs/`, so a command added without
regenerating fails the build.
"""

from __future__ import annotations

import io
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "COMMANDS.md"

HEADER = (
    "_Auto-generated from the CLI (`python scripts/gen_docs.py`)._\n\n"
    "_Every command also accepts `--output/-o` (json\\|table\\|markdown\\|csv), "
    "`--format/-f`, `--fields`/`--columns`, `--dry-run`, `--stream` and "
    "`--no-context`. Those are **stripped from argv before parsing**, so they work "
    "anywhere on the line — before or after the subcommand. `--profile/-p` and "
    "`--no-color` are ordinary root options and must therefore come **before** the "
    "subcommand (`lexware-office -p prod invoice ls`, not "
    "`lexware-office invoice ls -p prod`)._\n\n"
)


def _is_argument(p) -> bool:
    return getattr(p, "param_type_name", "") == "argument"


def _param_row(p) -> str | None:
    if _is_argument(p):
        return None
    opts = ", ".join(f"`{o}`" for o in list(p.opts) + list(p.secondary_opts))
    help_text = (getattr(p, "help", "") or "").replace("\n", " ").replace("|", "\\|")
    req = " **(required)**" if p.required else ""
    return f"| {opts} | {help_text}{req} |"


def _arguments(cmd) -> list[str]:
    out = []
    for p in cmd.params:
        if _is_argument(p):
            out.append(f"`{p.name}` ({'required' if p.required else 'optional'})")
    return out


def _emit_command(buf: io.StringIO, path: str, cmd) -> None:
    buf.write(f"### `lexware-office {path}`\n\n")
    help_text = (cmd.help or getattr(cmd, "short_help", "") or "").strip()
    if help_text:
        buf.write(help_text + "\n\n")
    args = _arguments(cmd)
    if args:
        buf.write("**Arguments:** " + ", ".join(args) + "\n\n")
    rows = [r for r in (_param_row(p) for p in cmd.params) if r]
    if rows:
        buf.write("| Option | Description |\n| --- | --- |\n")
        buf.write("\n".join(rows) + "\n\n")


def render(root) -> str:
    """Render the whole reference from a Click group. Pure — takes the app, returns text."""
    buf = io.StringIO()
    buf.write("# Command reference\n\n")
    buf.write(HEADER)

    groups = sorted(root.commands.items())
    buf.write("## Groups\n\n")
    for name, grp in groups:
        desc = (grp.help or getattr(grp, "short_help", "") or "").strip().split("\n")[0]
        buf.write(f"- [`{name}`](#{name}) — {desc}\n")
    buf.write("\n")

    for name, grp in groups:
        buf.write(f"## `{name}`\n\n")
        if hasattr(grp, "commands"):
            for sub_name, sub in sorted(grp.commands.items()):
                _emit_command(buf, f"{name} {sub_name}", sub)
        else:
            _emit_command(buf, name, grp)
    return buf.getvalue()


def main() -> None:
    # Imported inside main so the pure renderers above stay importable (and
    # testable) without pulling in httpx/rich/keyring and the whole command tree.
    import typer

    from lexwareoffice.cli import app

    root = typer.main.get_command(app)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(root))
    n_groups = len(root.commands)
    n_cmds = sum(len(g.commands) if hasattr(g, "commands") else 1 for g in root.commands.values())
    print(f"wrote {OUT} ({n_groups} groups, {n_cmds} commands)")


if __name__ == "__main__":
    main()

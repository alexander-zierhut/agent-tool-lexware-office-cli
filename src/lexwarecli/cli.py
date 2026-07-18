"""Top-level Typer application."""

from __future__ import annotations

import os
import sys

import typer
from agentcli import OutputFormat, print_error
from agentcli.errors import DryRun, OpError

from . import __version__
from .appctx import AppContext


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


app = typer.Typer(
    name="lexware-cli",
    help=(
        "Agent-friendly CLI for Lexware Office: contacts, invoices, and the "
        "receivables/AR-aging the API refuses to total for you.\n\n"
        "Output is JSON on stdout by default (errors are JSON on stderr with a "
        "non-zero exit code); add `-o table` or trim with `--fields`. The client "
        "paces itself under the 2 req/s limit automatically.\n\n"
        "New here? Run `lexware-cli guide`.  Start with `lexware-cli receivables` "
        "to see who owes you money."
    ),
    epilog="Learn more:  `lexware-cli guide`  ·  `lexware-cli guide <topic>`",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,  # locals hold the API key
)

_ERROR_FORMAT = OutputFormat.json


@app.callback()
def _root(
    ctx: typer.Context,
    output: OutputFormat = typer.Option(None, "--output", "-o", help="json (default), table, markdown, csv. Also --format/-f, anywhere on the line."),
    fields: str = typer.Option(None, "--fields", "--columns", help="Comma-separated fields, e.g. 'voucherNumber,openAmount'. Anywhere on the line."),
    profile: str = typer.Option(None, "--profile", "-p", help="Configuration profile."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Mutating commands: print the request that would be sent and exit."),
    stream: bool = typer.Option(False, "--stream", help="Stream results as NDJSON."),
    no_context: bool = typer.Option(False, "--no-context", help="Ignore the saved session context for this command."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable coloured output."),
    version: bool = typer.Option(None, "--version", "-V", callback=_version_callback, is_eager=True, help="Show version and exit."),
) -> None:
    if profile:
        os.environ["LEXWARECLI_PROFILE"] = profile
    meta = ctx.invoked_subcommand in ("settings", "guide", "install", "context")
    interactive = (
        not meta and sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get("CI") != "true"
    )
    ctx.obj = AppContext(output=output, color=not no_color, interactive=interactive)
    global _ERROR_FORMAT
    _ERROR_FORMAT = ctx.obj.emitter.fmt


_FORMAT_FLAGS = ("--format", "-f", "--output", "-o")
_FIELDS_FLAGS = ("--fields", "--columns")
_BOOL_FLAGS = ("--dry-run", "--stream", "--no-context")


def _pop_globals(argv: list[str]) -> tuple[str | None, str | None, set[str], list[str]]:
    out: list[str] = []
    fmt: str | None = None
    fields: str | None = None
    bools: set[str] = set()
    i, stop = 0, False

    def take(idx):
        return (argv[idx + 1], idx + 1) if idx + 1 < len(argv) else (None, idx)

    while i < len(argv):
        a = argv[i]
        if not stop and a == "--":
            stop = True
            out.append(a)
        elif not stop and a in _FORMAT_FLAGS:
            fmt, i = take(i)
        elif not stop and a in _FIELDS_FLAGS:
            fields, i = take(i)
        elif not stop and a in _BOOL_FLAGS:
            bools.add(a.lstrip("-"))
        elif not stop and any(a.startswith(p + "=") for p in _FORMAT_FLAGS):
            fmt = a.split("=", 1)[1]
        elif not stop and any(a.startswith(p + "=") for p in _FIELDS_FLAGS):
            fields = a.split("=", 1)[1]
        else:
            out.append(a)
        i += 1
    return fmt, fields, bools, out


from .commands import (  # noqa: E402
    article,
    auth,
    contact,
    context as context_cmd,
    file as file_cmd,
    guide,
    install,
    invoice,
    profile as profile_cmd,
    raw,
    receivables,
    recurring,
    reference,
    settings,
    voucher,
    webhook,
)
from .commands._salesdoc import make_group  # noqa: E402

app.command("guide", help="Built-in operating guide — how to use this CLI without external docs.")(guide.guide)

# Top-level, because it's the thing you came for: "who owes me money?"
app.command("receivables", help="Outstanding receivables + AR aging — the number the API won't total.")(receivables.receivables)

app.add_typer(contact.app, name="contact", help="Customers & vendors: list, get, create, update.")
app.add_typer(invoice.app, name="invoice", help="Invoices: list, get, create, finalize, payments, PDF.")

# The six other sales-document types share invoices' shape (see commands/_salesdoc.py).
app.add_typer(make_group("quotation"), name="quotation", help="Quotations (Angebote): list, get, create, PDF.")
app.add_typer(make_group("order-confirmation"), name="order-confirmation", help="Order confirmations (Auftragsbestätigungen).")
app.add_typer(make_group("credit-note"), name="credit-note", help="Credit notes (Gutschriften).")
app.add_typer(make_group("delivery-note"), name="delivery-note", help="Delivery notes (Lieferscheine).")
app.add_typer(make_group("down-payment-invoice"), name="down-payment-invoice", help="Down-payment invoices (read-only).")
app.add_typer(make_group("dunning"), name="dunning", help="Dunnings (Mahnungen) — require a preceding invoice.")

app.add_typer(article.app, name="article", help="Articles: products & services catalogue.")
app.add_typer(voucher.app, name="voucher", help="Bookkeeping vouchers (accounting entries).")
app.add_typer(webhook.app, name="webhook", help="Webhooks: subscribe to events, list, delete.")
app.add_typer(reference.app, name="reference", help="Reference data: countries, categories, payment conditions.")
app.add_typer(recurring.app, name="recurring", help="Recurring invoice templates (read-only).")
app.add_typer(file_cmd.app, name="file", help="Download stored files by id.")
app.add_typer(auth.app, name="auth", help="Log in, log out, inspect credentials.")
app.add_typer(profile_cmd.app, name="profile", help="The connected organisation — and what your key can do.")
app.add_typer(raw.app, name="raw", help="Escape hatch: call any API path directly.")
app.add_typer(settings.app, name="settings", help="View & change CLI settings.")
app.add_typer(context_cmd.app, name="context", help="Sticky session defaults, per profile.")
app.add_typer(install.app, name="install", help="Integrate with other tools (e.g. `install claude`).")


def main() -> None:
    import json as _json

    fmt, fields, bools, argv = _pop_globals(sys.argv[1:])
    if fmt is not None:
        os.environ["LEXWARECLI_CLI_FORMAT"] = fmt
    if fields is not None:
        os.environ["LEXWARECLI_CLI_FIELDS"] = fields
    if "dry-run" in bools:
        os.environ["LEXWARECLI_DRY_RUN"] = "1"
    if "stream" in bools:
        os.environ["LEXWARECLI_STREAM"] = "1"
    if "no-context" in bools:
        os.environ["LEXWARECLI_NO_CONTEXT"] = "1"
    try:
        app(args=argv)
    except DryRun as dr:
        sys.stdout.write(_json.dumps({"dryRun": True, "request": dr.request}, indent=2, default=str) + "\n")
        sys.exit(0)
    except OpError as exc:
        print_error(exc, _ERROR_FORMAT)
        sys.exit(exc.exit_code)
    except ValueError as exc:
        print_error(OpError(str(exc)), _ERROR_FORMAT)
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover
        print_error(OpError("interrupted"), _ERROR_FORMAT)
        sys.exit(130)


if __name__ == "__main__":  # pragma: no cover
    main()

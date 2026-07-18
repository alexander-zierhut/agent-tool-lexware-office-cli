"""Authentication — log in, log out, inspect the stored key."""

from __future__ import annotations

import sys

import typer

from ..config import PROD_URL, SANDBOX_URL, Profile
from ..errors import AuthError, ConfigError
from ..spec import credentials, token_url
from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


@app.command("login")
def login(
    ctx: typer.Context,
    profile: str = typer.Option(None, "--profile", "-p", help="Profile name (default: 'default')."),
    token: str = typer.Option(None, "--token", help="API key (else prompted)."),
    sandbox: bool = typer.Option(False, "--sandbox", help="Use the sandbox API (api.lexware-sandbox.io)."),
    url: str = typer.Option(None, "--url", help="Override the API base URL."),
) -> None:
    """Store an API key for a profile, after verifying it against `/v1/profile`."""
    obj = ctx_obj(ctx)
    name = profile or "default"
    base = url or (SANDBOX_URL if sandbox else PROD_URL)

    if not token:
        if not sys.stdin.isatty():
            raise ConfigError("--token is required when stdin is not a terminal.")
        sys.stderr.write(
            f"\nCreate an API key at:\n  {token_url(base)}\n\n"
            "Paste it below (input hidden). A Viewer/Editor key both work for reading;\n"
            "creating invoices needs write access.\n\n"
        )
        token = typer.prompt("API key", hide_input=True)
    if not token:
        raise ConfigError("an API key is required.")

    # Verify BEFORE persisting.
    from ..client import Client

    client = Client(base, token)
    try:
        prof_data = client.profile()
    except AuthError as exc:
        raise AuthError(f"that key was rejected by {base}: {exc}") from exc
    finally:
        client.close()

    p = Profile(
        name=name,
        base_url=base,
        company_name=(prof_data or {}).get("companyName"),
        organization_id=(prof_data or {}).get("organizationId"),
    )
    obj.config.upsert_profile(p)
    obj.config.save()
    backend = credentials.store_token(name, token)
    obj.emitter.emit({"profile": name, "baseUrl": base, "companyName": p.company_name, "storedIn": backend})


@app.command("status")
def status(ctx: typer.Context) -> None:
    """Which key/backend is in use, and for which organisation."""
    obj = ctx_obj(ctx)
    name = obj.config.active_profile_name()
    prof = obj.config.resolve()
    has = bool(credentials.get_token(name))
    obj.emitter.emit({
        "profile": name,
        "baseUrl": prof.base_url,
        "companyName": prof.company_name,
        "organizationId": prof.organization_id,
        "hasToken": has,
        "tokenBackend": credentials.backend_name() if has else None,
    })


@app.command("logout")
def logout(ctx: typer.Context, profile: str = typer.Option(None, "--profile", "-p")) -> None:
    """Delete the stored key for a profile."""
    obj = ctx_obj(ctx)
    name = profile or obj.config.active_profile_name()
    credentials.delete_token(name)
    obj.emitter.emit({"profile": name, "loggedOut": True})

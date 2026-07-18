"""This tool's identity, and the shared services derived from it."""

from __future__ import annotations

from agentcli import AppSpec, Credentials

SPEC = AppSpec(
    name="lexware-office",
    env_prefix="LEXWAREOFFICE",
    # The ecosystem's names, honoured AFTER ours. Lexware's own SDKs and most CI
    # recipes export LEXWARE_API_KEY (and the older LEXOFFICE_API_KEY).
    token_env_aliases=("LEXWARE_API_KEY", "LEXOFFICE_API_KEY"),
)

credentials = Credentials(SPEC)


def token_url(server: str) -> str:
    """Where a human creates an API key. Deriving it from what they typed beats
    telling them to "go find it"."""
    # The public-API add-on page. The sandbox host mirrors it under -sandbox.
    if "sandbox" in server:
        return "https://app.lexware-sandbox.de/addons/public-api"
    return "https://app.lexware.de/addons/public-api"

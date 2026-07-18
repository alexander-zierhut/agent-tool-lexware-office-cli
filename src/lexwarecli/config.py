"""Non-secret configuration: connection profiles and settings."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentcli.errors import ConfigError

from .spec import SPEC

DEFAULT_PROFILE = "default"
PROD_URL = "https://api.lexware.io"
SANDBOX_URL = "https://api.lexware-sandbox.io"


def config_dir() -> Path:
    return SPEC.config_dir()


def config_path() -> Path:
    return SPEC.config_file()


@dataclass
class Profile:
    name: str
    base_url: str = PROD_URL
    company_name: str | None = None       # informational; from /v1/profile
    organization_id: str | None = None
    verify_ssl: bool = True


@dataclass
class Config:
    current_profile: str = DEFAULT_PROFILE
    profiles: dict[str, Profile] = field(default_factory=dict)

    default_format: str | None = None     # None = never chosen -> ask once
    claude_prompted: bool = False
    contexts: dict[str, dict] = field(default_factory=dict)

    # ---- persistence -------------------------------------------------
    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text())
            profiles = {
                name: Profile(
                    name=name,
                    base_url=p.get("base_url", PROD_URL),
                    company_name=p.get("company_name"),
                    organization_id=p.get("organization_id"),
                    verify_ssl=p.get("verify_ssl", True),
                )
                for name, p in raw.get("profiles", {}).items()
            }
            return cls(
                current_profile=raw.get("current_profile", DEFAULT_PROFILE),
                profiles=profiles,
                default_format=raw.get("default_format"),
                claude_prompted=bool(raw.get("claude_prompted", False)),
                contexts=raw.get("contexts") or {},
            )
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ConfigError(f"malformed config at {path}: {exc}") from exc

    def save(self) -> None:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "current_profile": self.current_profile,
            "default_format": self.default_format,
            "claude_prompted": self.claude_prompted,
            "contexts": self.contexts,
            "profiles": {
                name: {
                    "base_url": p.base_url,
                    "company_name": p.company_name,
                    "organization_id": p.organization_id,
                    "verify_ssl": p.verify_ssl,
                }
                for name, p in self.profiles.items()
            },
        }
        path.write_text(json.dumps(data, indent=2) + "\n")

    # ---- resolution --------------------------------------------------
    def active_profile_name(self) -> str:
        return SPEC.getenv("PROFILE") or self.current_profile

    def _env_url(self) -> str | None:
        return SPEC.getenv("URL") or os.environ.get("LEXWARE_URL")

    def resolve(self) -> Profile:
        name = self.active_profile_name()
        env_url = self._env_url()
        prof = self.profiles.get(name)
        if prof is None:
            if env_url:
                return Profile(name=name, base_url=env_url)
            raise ConfigError(
                f"no profile '{name}' configured. Run `lexware-cli auth login` "
                f"or set LEXWARE_API_KEY (+ LEXWARE_URL for the sandbox)."
            )
        return Profile(
            name=prof.name,
            base_url=env_url or prof.base_url,
            company_name=prof.company_name,
            organization_id=prof.organization_id,
            verify_ssl=prof.verify_ssl,
        )

    def upsert_profile(self, prof: Profile, make_current: bool = True) -> None:
        self.profiles[prof.name] = prof
        if make_current:
            self.current_profile = prof.name

    @property
    def context(self) -> dict:
        return self.contexts.get(self.active_profile_name()) or {}

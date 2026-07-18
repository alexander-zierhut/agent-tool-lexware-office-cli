"""Reserved global flags + guide/skill honesty — hermetic, introspection only."""

from __future__ import annotations

import re

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from lexwareoffice.cli import _BOOL_FLAGS, _FIELDS_FLAGS, _FORMAT_FLAGS, _pop_globals, app

RESERVED = set(_FORMAT_FLAGS) | set(_FIELDS_FLAGS) | set(_BOOL_FLAGS)


def _walk(cmd, path=""):
    subs = getattr(cmd, "commands", None)
    if subs:
        for name, sub in subs.items():
            yield from _walk(sub, f"{path} {name}".strip())
    else:
        yield path, cmd


def _leaves():
    return list(_walk(get_command(app)))


def test_the_tree_has_commands():
    assert len(_leaves()) > 15


def test_no_command_declares_a_reserved_global():
    offenders = []
    for path, cmd in _leaves():
        if not path:
            continue
        for p in cmd.params:
            if getattr(p, "param_type_name", "") != "option":
                continue
            clash = sorted(set(p.opts) & RESERVED)
            if clash:
                offenders.append(f"  `lexware-office {path}` declares {clash}")
    assert not offenders, "reserved globals can never be received:\n" + "\n".join(offenders)


def test_file_outputs_use_out_not_output():
    """--output is a reserved format flag; any file destination must be --out."""
    for path, cmd in _leaves():
        opts = {o for p in cmd.params for o in getattr(p, "opts", [])}
        assert "--output" not in opts, f"`lexware-office {path}` uses --output (reserved); use --out"


# ---- _pop_globals ----------------------------------------------------

def test_pops_format_from_anywhere():
    for argv in (["-o", "table", "receivables"], ["receivables", "-o", "table"]):
        fmt, _f, _b, rest = _pop_globals(argv)
        assert fmt == "table" and rest == ["receivables"]


def test_pops_dry_run():
    _f, _fl, bools, rest = _pop_globals(["invoice", "create", "--dry-run"])
    assert "dry-run" in bools and rest == ["invoice", "create"]


def test_double_dash_stops_parsing():
    fmt, _f, _b, rest = _pop_globals(["raw", "get", "--", "-o", "x"])
    assert fmt is None and rest == ["raw", "get", "--", "-o", "x"]


# ---- guide honesty ---------------------------------------------------

def test_guide_commands_all_exist():
    from lexwareoffice.commands import guide as G

    real = {p for p, _ in _leaves() if p}
    groups = {p.split()[0] for p in real}
    text = G.OVERVIEW + "".join(G.TOPICS.values())
    named = set()
    for m in re.finditer(r"\blexware-office\s+([a-z][\w-]*)(?:\s+([a-z][\w-]*))?", text):
        first, second = m.group(1), m.group(2)
        cand = f"{first} {second}" if second else first
        named.add((cand, first))
    broken = []
    for cand, head in named:
        if cand in real or cand in groups:
            continue
        if head in groups or head in real:
            continue  # command-with-argument (e.g. `guide gotchas`, `receivables --view`)
        broken.append(cand)
    assert not broken, f"guide names nonexistent commands: {broken}"


def test_guide_has_a_gotchas_topic():
    from lexwareoffice.commands import guide as G

    assert "gotchas" in G.TOPICS


@pytest.mark.parametrize("topic", ["receivables", "invoices", "contacts", "auth", "pacing", "output", "gotchas"])
def test_every_topic_renders(topic):
    r = CliRunner().invoke(app, ["guide", topic])
    assert r.exit_code == 0 and r.stdout.strip()


def test_guide_needs_no_config(monkeypatch, tmp_path):
    monkeypatch.setenv("LEXWAREOFFICE_CONFIG_DIR", str(tmp_path / "nope"))
    r = CliRunner().invoke(app, ["guide"])
    assert r.exit_code == 0 and "lexware-office" in r.stdout


def test_skill_only_names_real_commands():
    from lexwareoffice.commands import guide as G  # noqa: F401
    from lexwareoffice.commands import install as I

    real = {p for p, _ in _leaves() if p}
    groups = {p.split()[0] for p in real}
    broken = []
    for m in re.finditer(r"`lexware-office\s+([a-z][\w-]*)(?:\s+([a-z][\w|-]*))?", I.SKILL_MD):
        head = m.group(1)
        if head not in groups and head not in real:
            broken.append(head)
    assert not broken, f"SKILL.md names nonexistent commands: {sorted(set(broken))}"

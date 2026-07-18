"""Contacts — customers & vendors."""

from __future__ import annotations

import typer

from ..errors import ValidationError
from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


def _row(c: dict) -> dict:
    roles = c.get("roles") or {}
    name = (c.get("company") or {}).get("name") or _person_name(c.get("person") or {})
    return {
        "id": c.get("id"),
        "name": name,
        "type": "company" if c.get("company") else "person",
        "customer": (roles.get("customer") or {}).get("number") if "customer" in roles else None,
        "vendor": (roles.get("vendor") or {}).get("number") if "vendor" in roles else None,
    }


def _person_name(p: dict) -> str:
    return f"{p.get('lastName', '')}, {p.get('firstName', '')}".strip(", ").strip()


@app.command("list")
def list_(
    ctx: typer.Context,
    customer: bool = typer.Option(False, "--customer", help="Only customers."),
    vendor: bool = typer.Option(False, "--vendor", help="Only vendors."),
    name: str = typer.Option(None, "--name", help="Name filter (>=3 chars, substring)."),
    email: str = typer.Option(None, "--email", help="Email filter (>=3 chars, substring)."),
    limit: int = typer.Option(100, "--limit", help="Max contacts to return (0 = all)."),
) -> None:
    """List contacts (paginated + paced automatically)."""
    obj = ctx_obj(ctx)
    params = {}
    if customer:
        params["customer"] = "true"
    if vendor:
        params["vendor"] = "true"
    if name:
        params["name"] = name
    if email:
        params["email"] = email
    rows = [_row(c) for c in obj.client().paginate("/contacts", params=params, size=100, limit=limit)]
    obj.emitter.emit(rows, columns=["id", "name", "type", "customer", "vendor"])


@app.command("get")
def get(ctx: typer.Context, contact_id: str = typer.Argument(..., help="Contact id (UUID).")) -> None:
    """Retrieve one contact (the full object, incl. the assigned number)."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get(f"/contacts/{contact_id}"))


@app.command("create")
def create(
    ctx: typer.Context,
    company: str = typer.Option(None, "--company", help="Company name (company contact)."),
    first_name: str = typer.Option(None, "--first-name"),
    last_name: str = typer.Option(None, "--last-name"),
    role: str = typer.Option("customer", "--role", help="customer | vendor | both."),
) -> None:
    """Create a contact. Returns the action-result; the assigned customer/vendor
    number is fetched and included (the create result omits it)."""
    obj = ctx_obj(ctx)
    if bool(company) == bool(last_name):
        raise ValidationError("give exactly one of --company OR --last-name (company XOR person).")
    roles = {}
    if role in ("customer", "both"):
        roles["customer"] = {}
    if role in ("vendor", "both"):
        roles["vendor"] = {}
    if not roles:
        raise ValidationError("--role must be customer, vendor, or both.")
    body: dict = {"version": 0, "roles": roles}
    if company:
        body["company"] = {"name": company}
    else:
        body["person"] = {"firstName": first_name or "", "lastName": last_name}
    result = obj.client().post("/contacts", json=body)
    # The create result omits the number — fetch the object so the caller sees it.
    if isinstance(result, dict) and result.get("id") and not obj.client().dry_run:
        try:
            result = {"actionResult": result, "contact": obj.client().get(f"/contacts/{result['id']}")}
        except Exception:
            pass
    obj.emitter.emit(result)

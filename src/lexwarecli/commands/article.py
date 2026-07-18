"""Articles — products & services (the line-item catalogue)."""

from __future__ import annotations

import typer

from ..errors import ValidationError
from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


def _row(a: dict) -> dict:
    price = a.get("price") or {}
    return {
        "id": a.get("id"),
        "title": a.get("title"),
        "type": a.get("type"),
        "articleNumber": a.get("articleNumber"),
        "netPrice": price.get("netPrice"),
        "unitName": a.get("unitName"),
    }


@app.command("list")
def list_(
    ctx: typer.Context,
    number: str = typer.Option(None, "--number", help="Filter by articleNumber."),
    gtin: str = typer.Option(None, "--gtin", help="Filter by GTIN."),
    limit: int = typer.Option(100, "--limit"),
) -> None:
    """List articles (paginated)."""
    obj = ctx_obj(ctx)
    params = {}
    if number:
        params["articleNumber"] = number
    if gtin:
        params["gtin"] = gtin
    rows = [_row(a) for a in obj.client().paginate("/articles", params=params, size=100, limit=limit)]
    obj.emitter.emit(rows, columns=["id", "title", "type", "articleNumber", "netPrice", "unitName"])


@app.command("get")
def get(ctx: typer.Context, article_id: str = typer.Argument(...)) -> None:
    """Retrieve one article."""
    obj = ctx_obj(ctx)
    obj.emitter.emit(obj.client().get(f"/articles/{article_id}"))


@app.command("create")
def create(
    ctx: typer.Context,
    title: str = typer.Option(..., "--title"),
    type_: str = typer.Option("SERVICE", "--type", help="PRODUCT | SERVICE (uppercase)."),
    net: float = typer.Option(..., "--net", help="Net price (EUR)."),
    tax: float = typer.Option(19, "--tax", help="Tax rate percent."),
    unit: str = typer.Option("Stück", "--unit"),
    number: str = typer.Option(None, "--number", help="articleNumber."),
) -> None:
    """Create a product/service article. `type` is uppercase PRODUCT|SERVICE."""
    obj = ctx_obj(ctx)
    if type_ not in ("PRODUCT", "SERVICE"):
        raise ValidationError("--type must be PRODUCT or SERVICE (uppercase).")
    body = {"title": title, "type": type_, "unitName": unit, "price": {"netPrice": net, "leadingPrice": "NET", "taxRate": tax}}
    if number:
        body["articleNumber"] = number
    obj.emitter.emit(obj.client().post("/articles", json=body))


@app.command("delete")
def delete(ctx: typer.Context, article_id: str = typer.Argument(...), yes: bool = typer.Option(False, "--yes", "-y")) -> None:
    """Delete an article."""
    obj = ctx_obj(ctx)
    if not yes and obj.interactive:
        typer.confirm(f"Delete article {article_id}?", abort=True)
    obj.client().delete(f"/articles/{article_id}")
    obj.emitter.emit({"id": article_id, "deleted": True})

"""Files — download a stored file (e.g. a rendered document or an uploaded receipt)."""

from __future__ import annotations

from pathlib import Path

import typer

from ..errors import ValidationError
from ._shared import ctx_obj

app = typer.Typer(no_args_is_help=True)


@app.command("download")
def download(
    ctx: typer.Context,
    file_id: str = typer.Argument(..., help="File id (UUID)."),
    out: str = typer.Option(..., "--out", help="Where to save the file."),
) -> None:
    """Download a file by id to `--out`. Binary carve-out — the JSON reports the path."""
    obj = ctx_obj(ctx)
    data = obj.client().get(f"/files/{file_id}", raw=True)
    if not isinstance(data, (bytes, bytearray)):
        raise ValidationError("the server did not return file bytes.")
    dest = Path(out)
    dest.write_bytes(data)
    obj.emitter.emit({"file": str(dest.resolve()), "bytes": len(data)})

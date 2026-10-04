"""Export reading views of DocIR tables."""

from __future__ import annotations

import json
from pathlib import Path

import click
from cpushowspeed.documents.rich_table import render_table_block


@click.command("render-tables")
@click.argument("docir", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option("--page", type=click.IntRange(1), help="One physical PDF page; default is all pages.")
def render_tables_command(docir, page):
    """Render stored table blocks as Markdown to stdout."""
    try:
        with docir.open() as f:
            for line in f:
                record = json.loads(line)
                if page is not None and page != record["page"]:
                    continue
                for i, block in enumerate(record["blocks"]):
                    if block.get("kind") == "table":
                        click.echo(f"## PDF page {record['page']}, block {i}\n")
                        if block.get("conversion_status") == "failed":
                            click.echo("[Unconverted table; inspect original PDF and raw OCR.]\n")
                        else:
                            click.echo(render_table_block(block) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc

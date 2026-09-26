"""Command-line entry point for CPUShowSpeed."""

import click
from cpushowspeed.annual_rate import plot
from cpushowspeed.annual_rate_ci import annual_rate_ci_command
from cpushowspeed.bridge import bridge
from cpushowspeed.caption import caption_command
from cpushowspeed.caption_backfill import backfill_captions_command
from cpushowspeed.documents import documents
from cpushowspeed.ocr import ocr_command
from cpushowspeed.rate_convert import convert_rate_command
from cpushowspeed.spec import spec
from cpushowspeed.spec89 import spec89
from cpushowspeed.spec92_rate import legacy92_rate_parse_command
from cpushowspeed.table_migrate import migrate_tables_command, render_tables_command


@click.group()
@click.version_option(package_name="cpushowspeed")
def cli() -> None:
    """Collect and analyze historical CPU performance evidence."""


spec.add_command(legacy92_rate_parse_command)
cli.add_command(spec)
cli.add_command(convert_rate_command)
cli.add_command(spec89)
cli.add_command(bridge)
plot.add_command(annual_rate_ci_command)
cli.add_command(plot)
documents.add_command(ocr_command)
documents.add_command(caption_command)
documents.add_command(backfill_captions_command)
documents.add_command(migrate_tables_command)
documents.add_command(render_tables_command)
cli.add_command(documents)

"""Command-line entry point for CPUShowSpeed."""

import click
from cpushowspeed.annual_rate import plot
from cpushowspeed.annual_rate_ci import annual_rate_ci_command
from cpushowspeed.bridge import bridge
from cpushowspeed.caption import caption_command
from cpushowspeed.caption_backfill import backfill_captions_command
from cpushowspeed.classic import classic
from cpushowspeed.classic_89_rate import spec89_rate_fit
from cpushowspeed.classic_composite import composite_overlap
from cpushowspeed.classic_composite_fit import composite_fit
from cpushowspeed.classic_diagnostics import source_diagnostics
from cpushowspeed.classic_environment import environment_fit
from cpushowspeed.classic_fit import fit_spec92
from cpushowspeed.classic_overlap import overlap_spec
from cpushowspeed.classic_pair_fit import pair_fit
from cpushowspeed.classic_pdf import extract_pdf_tables
from cpushowspeed.classic_pooled import pooled_fit
from cpushowspeed.classic_rate_composite import rate_composite_fit
from cpushowspeed.classic_source_fit import source_pair_fit
from cpushowspeed.documents import documents
from cpushowspeed.ocr import ocr_command
from cpushowspeed.rate_convert import convert_rate_command
from cpushowspeed.research_registry import research
from cpushowspeed.spec import spec
from cpushowspeed.spec89 import spec89
from cpushowspeed.spec92_rate import legacy92_rate_parse_command
from cpushowspeed.table_migrate import migrate_tables_command, render_tables_command


@click.group()
@click.version_option(package_name="cpushowspeed")
def cli() -> None:
    """Collect and analyze historical CPU performance evidence."""


spec.add_command(legacy92_rate_parse_command)
cli.add_command(research)
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
classic.add_command(overlap_spec)
classic.add_command(fit_spec92)
classic.add_command(composite_overlap)
classic.add_command(composite_fit)
classic.add_command(pair_fit)
classic.add_command(extract_pdf_tables)
classic.add_command(source_pair_fit)
classic.add_command(source_diagnostics)
classic.add_command(environment_fit)
classic.add_command(pooled_fit)
classic.add_command(rate_composite_fit)
classic.add_command(spec89_rate_fit)
cli.add_command(classic)

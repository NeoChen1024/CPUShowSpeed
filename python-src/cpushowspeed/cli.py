"""Command-line entry point for CPUShowSpeed."""

import click
from cpushowspeed.classic_bench import bench
from cpushowspeed.classical.collect import classic
from cpushowspeed.classical.composite_fit import composite_fit, spec89_fit
from cpushowspeed.classical.network_fit import network_fit
from cpushowspeed.classical.pdf_tables import extract_pdf_tables
from cpushowspeed.classical.power_law import power_law_sensitivity
from cpushowspeed.classical.source_parsers import parse_sources_command
from cpushowspeed.database.curated_tables import data
from cpushowspeed.database.processor_identity import extract_command
from cpushowspeed.documents.caption import caption_command
from cpushowspeed.documents.caption_backfill import backfill_captions_command
from cpushowspeed.documents.inventory import documents
from cpushowspeed.documents.ocr import ocr_command
from cpushowspeed.documents.table_views import render_tables_command
from cpushowspeed.mix.classical_fit import mix_bridge
from cpushowspeed.mix.inventory import mix_inventory
from cpushowspeed.mix.network_fit import mix_network_fit
from cpushowspeed.mix.ocr_evidence import mix_evidence
from cpushowspeed.research_registry import research
from cpushowspeed.spec89.cli import spec89
from cpushowspeed.spec.chain_cli import chain
from cpushowspeed.spec.collect import spec
from cpushowspeed.spec.cpu92_rate import cpu92_rate_parse_command
from cpushowspeed.spec.field_audit import audit_fields, fetch_resources
from cpushowspeed.timeline.build import timeline_command


@click.group()
@click.version_option(package_name="cpushowspeed")
def cli() -> None:
    """Collect and analyze historical CPU performance evidence."""


@click.group()
def plot() -> None:
    """Render the combined VAXen timeline."""


@click.group()
def mix() -> None:
    """Instruction-mix ratings: source inventory, OCR evidence and fits against classical results."""


spec.add_command(cpu92_rate_parse_command)
cli.add_command(research)
data.add_command(extract_command)
cli.add_command(data)

spec.add_command(audit_fields)
spec.add_command(fetch_resources)
cli.add_command(spec)
cli.add_command(spec89)
cli.add_command(chain)
plot.add_command(timeline_command)
cli.add_command(plot)
documents.add_command(ocr_command)
documents.add_command(caption_command)
documents.add_command(backfill_captions_command)
documents.add_command(render_tables_command)
cli.add_command(documents)
classic.add_command(parse_sources_command)
classic.add_command(extract_pdf_tables)
classic.add_command(composite_fit)
classic.add_command(spec89_fit)
classic.add_command(network_fit)
classic.add_command(power_law_sensitivity)
cli.add_command(classic)
mix.add_command(mix_inventory)
mix.add_command(mix_evidence)
mix.add_command(mix_bridge)
mix.add_command(mix_network_fit)
cli.add_command(mix)
cli.add_command(bench)

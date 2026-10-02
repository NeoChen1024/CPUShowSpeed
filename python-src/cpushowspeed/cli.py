"""Command-line entry point for CPUShowSpeed."""

from pathlib import Path

import click
from cpushowspeed.annual_rate import plot
from cpushowspeed.annual_rate_ci import annual_rate_ci_command
from cpushowspeed.bridge import bridge
from cpushowspeed.caption import caption_command
from cpushowspeed.caption_backfill import backfill_captions_command
from cpushowspeed.classic import classic
from cpushowspeed.classic_mix import mix_inventory
from cpushowspeed.classic_network import network_fit
from cpushowspeed.classic_overlap import overlap_spec
from cpushowspeed.classic_pdf import extract_pdf_tables
from cpushowspeed.classic_predict import predict_rate
from cpushowspeed.classic_timeline import historical_timeline
from cpushowspeed.classical_fit import rate_composite_fit, spec89_rate_fit
from cpushowspeed.cpu_chronology import cpu_chronology_command
from cpushowspeed.curated import data
from cpushowspeed.curated_dates import import_dates_command
from cpushowspeed.curated_identity import extract_command, import_processors_command
from cpushowspeed.curated_review import import_reviews_command
from cpushowspeed.curated_sources import migrate_sources_command
from cpushowspeed.curated_system import import_vendors_command
from cpushowspeed.documents import documents
from cpushowspeed.factor_review import compare_factors
from cpushowspeed.historical_candidates import year_candidates, year_evidence
from cpushowspeed.input_catalog import inputs
from cpushowspeed.input_context import ACTIVE_CATALOG
from cpushowspeed.mix_bridge import mix_bridge
from cpushowspeed.mix_evidence import mix_evidence
from cpushowspeed.ocr import ocr_command
from cpushowspeed.rate_convert import convert_rate_command
from cpushowspeed.research_registry import research
from cpushowspeed.spec import spec
from cpushowspeed.spec89 import spec89
from cpushowspeed.spec92_rate import legacy92_rate_parse_command
from cpushowspeed.spec_field_audit import audit_fields, fetch_resources
from cpushowspeed.table_migrate import migrate_tables_command, render_tables_command
from cpushowspeed.unified_timeline import timeline_command


@click.group()
@click.version_option(package_name="cpushowspeed")
@click.option(
    "--input-catalog",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    help="Use a hash-checked shared input snapshot for SPEC and classical network readers.",
)
@click.pass_context
def cli(ctx, input_catalog) -> None:
    """Collect and analyze historical CPU performance evidence."""
    token = ACTIVE_CATALOG.set(input_catalog)
    ctx.call_on_close(lambda: ACTIVE_CATALOG.reset(token))


@click.group("predict")
def predict():
    """Estimate VAXen from SPEC integer rate or classical benchmark scores."""


predict.add_command(convert_rate_command, name="spec-rate")
predict.add_command(predict_rate, name="classical")
cli.add_command(predict)


spec.add_command(legacy92_rate_parse_command)
research.add_command(cpu_chronology_command)
cli.add_command(research)
data.add_command(migrate_sources_command)
data.add_command(import_processors_command)
data.add_command(extract_command)
data.add_command(import_vendors_command)
data.add_command(import_dates_command)
data.add_command(import_reviews_command)
cli.add_command(data)

spec.add_command(audit_fields)
spec.add_command(fetch_resources)
cli.add_command(spec)
inputs.add_command(compare_factors)
cli.add_command(inputs)
cli.add_command(convert_rate_command)
cli.add_command(spec89)
cli.add_command(bridge)
plot.add_command(annual_rate_ci_command)
plot.add_command(timeline_command)
cli.add_command(plot)
documents.add_command(ocr_command)
documents.add_command(year_candidates)
documents.add_command(year_evidence)
documents.add_command(caption_command)
documents.add_command(backfill_captions_command)
documents.add_command(migrate_tables_command)
documents.add_command(render_tables_command)
cli.add_command(documents)
classic.add_command(overlap_spec)
classic.add_command(mix_inventory)
classic.add_command(extract_pdf_tables)
classic.add_command(rate_composite_fit)
classic.add_command(spec89_rate_fit)
classic.add_command(network_fit)
classic.add_command(predict_rate)
classic.add_command(historical_timeline)
classic.add_command(mix_evidence)
classic.add_command(mix_bridge)
cli.add_command(classic)

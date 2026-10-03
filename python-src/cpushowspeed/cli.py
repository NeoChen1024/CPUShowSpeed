"""Command-line entry point for CPUShowSpeed."""

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
from cpushowspeed.classic_power_law import power_law_sensitivity
from cpushowspeed.classic_predict import predict_speed
from cpushowspeed.classical_fit import composite_fit, spec89_fit
from cpushowspeed.curated import data
from cpushowspeed.curated_identity import extract_command
from cpushowspeed.curated_system import import_vendors_command
from cpushowspeed.documents import documents
from cpushowspeed.factor_review import compare_factors
from cpushowspeed.input_catalog import inputs
from cpushowspeed.mix_bridge import mix_bridge
from cpushowspeed.mix_evidence import mix_evidence
from cpushowspeed.mix_network import mix_network_fit
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
def cli() -> None:
    """Collect and analyze historical CPU performance evidence."""


@click.group("predict")
def predict():
    """Estimate VAXen from SPEC integer rate or classical benchmark scores."""


predict.add_command(convert_rate_command, name="spec-rate")
predict.add_command(predict_speed, name="classical")
cli.add_command(predict)


spec.add_command(legacy92_rate_parse_command)
cli.add_command(research)
data.add_command(extract_command)
data.add_command(import_vendors_command)
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
documents.add_command(caption_command)
documents.add_command(backfill_captions_command)
documents.add_command(migrate_tables_command)
documents.add_command(render_tables_command)
cli.add_command(documents)
classic.add_command(overlap_spec)
classic.add_command(mix_inventory)
classic.add_command(extract_pdf_tables)
classic.add_command(composite_fit)
classic.add_command(spec89_fit)
classic.add_command(network_fit)
classic.add_command(power_law_sensitivity)
classic.add_command(mix_network_fit)
classic.add_command(predict_speed)
classic.add_command(mix_evidence)
classic.add_command(mix_bridge)
cli.add_command(classic)

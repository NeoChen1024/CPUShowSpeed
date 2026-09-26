"""CLI for adjacent-generation SPEC integer-rate overlap analysis."""

import click
from cpushowspeed.spec92_rate_fit import fit_rate92_anchor_command
from cpushowspeed.spec_rate_chain import bootstrap_rate_chain_command
from cpushowspeed.spec_rate_fit import fit_rate_generations_command


@click.group()
def bridge() -> None:
    """Fit source-linked SPEC integer-rate overlaps."""


bridge.add_command(fit_rate_generations_command)
bridge.add_command(fit_rate92_anchor_command)

bridge.add_command(bootstrap_rate_chain_command)

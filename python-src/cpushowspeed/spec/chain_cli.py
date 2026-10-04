"""CLI for the SPEC integer-rate and integer-speed generation chains."""

import click
from cpushowspeed.spec.cpu92_rate_fit import fit_cpu92_rate_anchor_command
from cpushowspeed.spec.cpu95_cpu2000_audit import audit_cpu95_cpu2000_command
from cpushowspeed.spec.rate_chain import bootstrap_rate_command
from cpushowspeed.spec.rate_fit import fit_rate_generations_command
from cpushowspeed.spec.speed_chain import fit_speed_command


@click.group()
def chain() -> None:
    """Fit and audit the source-linked SPEC integer-rate and integer-speed generation chains."""


chain.add_command(fit_rate_generations_command)
chain.add_command(fit_cpu92_rate_anchor_command)
chain.add_command(bootstrap_rate_command)
chain.add_command(fit_speed_command)
chain.add_command(audit_cpu95_cpu2000_command)

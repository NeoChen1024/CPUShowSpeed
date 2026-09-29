"""CLI for adjacent-generation SPEC integer-rate overlap analysis."""

import click
from cpushowspeed.spec92_rate_fit import fit_rate92_anchor_command
from cpushowspeed.spec95_overlap_audit import audit_95_2000
from cpushowspeed.spec95_refit import refit_95_2000
from cpushowspeed.spec_dual_track import compare_tracks
from cpushowspeed.spec_joint_tracks import fit_joint_tracks
from cpushowspeed.spec_rate_chain import bootstrap_rate_chain_command
from cpushowspeed.spec_rate_fit import fit_rate_generations_command


@click.group()
def bridge() -> None:
    """Fit source-linked SPEC integer-rate overlaps."""


bridge.add_command(fit_rate_generations_command)
bridge.add_command(fit_rate92_anchor_command)

bridge.add_command(bootstrap_rate_chain_command)

bridge.add_command(compare_tracks)

bridge.add_command(fit_joint_tracks)

bridge.add_command(audit_95_2000)

bridge.add_command(refit_95_2000)

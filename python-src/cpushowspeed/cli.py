"""Command-line entry point for CPUShowSpeed."""

import click
from cpushowspeed.plot import plot
from cpushowspeed.spec import spec


@click.group()
@click.version_option(package_name="cpushowspeed")
def cli() -> None:
    """Collect and analyze historical CPU performance evidence."""


cli.add_command(spec)
cli.add_command(plot)

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from risos.runner import run_all, run_one

app = typer.Typer(name="risos")


@app.callback()
def main() -> None:
    """Universal RSS/Atom feed generator."""


@app.command()
def generate(
    all_sites: Annotated[
        bool, typer.Option("--all/--no-all", help="Process all YAML configs")
    ] = False,
    site: Annotated[
        Path | None, typer.Option("--site", help="Path to a specific YAML config")
    ] = None,
    sites_dir: Annotated[
        Path, typer.Option("--sites-dir", help="Directory with YAML configs")
    ] = Path("sites"),
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Output directory")] = Path(
        "output"
    ),
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable debug logging")] = False,
) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    if all_sites and site:
        typer.echo("Error: specify --all or --site, not both", err=True)
        raise typer.Exit(code=1)
    if not all_sites and not site:
        typer.echo("Error: specify --all or --site", err=True)
        raise typer.Exit(code=1)

    if all_sites:
        run_all(sites_dir, output_dir)
    elif site:
        run_one(site, output_dir)


if __name__ == "__main__":
    app()

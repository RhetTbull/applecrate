"""CLI for applecrate to build macOS installer packages."""

from __future__ import annotations

import os
import pathlib

import click
import toml
from click import echo

from .build import BUILD_DIR, build_installer, check_dependencies, validate_build_kwargs
from .utils import set_from_defaults


@click.group()
def cli():
    """applecrate: A Python package for creating macOS installer packages."""
    pass


# @cli.command()
# def init():
#     """Create a new applecrate project."""
#     echo("Creating a new applecrate project.")


# @cli.command()
# def check():
#     """Check the current environment for applecrate."""
#     echo("Checking the current environment for applecrate.")


@cli.command()
@click.option("--app", "-a", help="App name")
@click.option("--version", "-v", help="App version")
@click.option(
    "--license",
    "-l",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to license file. "
    "If provided, the installer will include a click-through license agreement.",
)
@click.option(
    "--welcome",
    "-w",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to welcome markdown or HTML file",
)
@click.option(
    "--conclusion",
    "-c",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to conclusion markdown or HTML file",
)
@click.option(
    "--uninstall",
    "-u",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to uninstall script; "
    "if not provided, an uninstall script will be created for you. "
    "See also '--no-uninstall'",
)
@click.option(
    "--no-uninstall",
    "-U",
    is_flag=True,
    help="Do not include an uninstall script in the package",
)
@click.option(
    "--url",
    "-L",
    metavar="NAME URL",
    multiple=True,
    nargs=2,
    help="Links to additional resources to include in conclusion HTML shown after installation. "
    "For example, the project website or documentation.",
)
@click.option(
    "--banner",
    "-b",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to optional PNG banner image for installer package.",
)
@click.option(
    "--install",
    "-i",
    metavar="FILE_OR_DIR DEST",
    nargs=2,
    multiple=True,
    help="Install FILE_OR_DIR to destination DEST; "
    "DEST must be an absolute path, for example '/usr/local/bin/app'. "
    r"DEST may include template variables {{ app }} and {{ version }}. "
    'For example: `--install dist/app "/usr/local/bin/{{ app }}-{{ version }}"` '
    "will install the file 'dist/app' to '/usr/local/bin/app-1.0.0' "
    "if --app=app and --version=1.0.0.",
)
@click.option(
    "--link",
    "-k",
    metavar="SRC TARGET",
    nargs=2,
    multiple=True,
    help="Create a symbolic link from SRC to DEST after installation. "
    "SRC and TARGET must be absolute paths and both may include template variables {{ app }} and {{ version }}. "
    'For example: `--link "/Library/Application Support/{{ app }}/{{ version }}/app" "/usr/local/bin/{{ app }}-{{ version }}"` ',
)
@click.option(
    "--pre-install",
    "-p",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to pre-install shell script; " "if not provided, a pre-install script will be created for you.",
)
@click.option(
    "--post-install",
    "-P",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to post-install shell script; "
    "if not provided, a post-install script will be created for you. "
    "If provided, the installer will run this script after other post-install actions.",
)
@click.option(
    "--chmod",
    "-m",
    metavar="MODE PATH",
    nargs=2,
    multiple=True,
    help="Change the mode of PATH to MODE after installation. "
    "PATH must be an absolute path. "
    "PATH may contain template variables {{ app }} and {{ version }}. "
    "MODE must be an octal number, for example '755'. ",
)
@click.option(
    "--sign",
    "-s",
    metavar="APPLE_DEVELOPER_CERTIFICATE_ID",
    help="Sign the installer package with a developer ID. "
    "If APPLE_DEVELOPER_CERTIFICATE_ID starts with '$', "
    "it will be treated as an environment variable "
    "and the value of the environment variable will be used as the developer ID.",
)
@click.option(
    "--build-dir",
    "-d",
    type=click.Path(file_okay=False, writable=True, exists=True),
    help="Build directory to use for building the installer package. " f"Default is {BUILD_DIR} if not provided.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    help="Path to save the installer package.",
)
def build(**kwargs):
    """applecrate: A Python package for creating macOS installer packages."""

    check_dependencies(verbose=echo)

    # configure precedence:
    # command line arguments take precedence over configuration files
    # applecrate.toml takes precedence over pyproject.toml
    # load in reverse order of precedence as the subsequent load will only
    # be used if the key is not already set
    if pathlib.Path("applecrate.toml").exists():
        kwargs = set_from_defaults(kwargs, load_from_toml("applecrate.toml"))
    if pathlib.Path("pyproject.toml").exists():
        kwargs = set_from_defaults(kwargs, load_from_toml("pyproject.toml"))
    try:
        validate_build_kwargs(**kwargs)
    except ValueError as e:
        raise click.BadParameter(str(e))
    build_installer(**kwargs, verbose=echo)


def load_from_toml(path: str | os.PathLike) -> dict[str, str]:
    """Load configuration from a TOML file.

    Args:
        path: The path to the TOML file.

    Returns: A dictionary of configuration values.

    Note: if the toml file is named 'pyproject.toml' then the configuration
    will be loaded from the 'tool.applecrate' section; otherwise, the configuration
    will be loaded from the root of the file.
    """
    path = pathlib.Path(path)
    data = toml.load(str(path))
    if path.name == "pyproject.toml":
        return data.get("tool", {}).get("applecrate", {})
    else:
        return data

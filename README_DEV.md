# Developer Notes

These are notes to help me (and other contributors) remember how to set up the project and do common tasks.

## Build Tool

This project uses [Flit](https://flit.readthedocs.io/en/latest/).  It is a simple build tool that uses `pyproject.toml` to define the project.

## Installing

- Create a virtual environment and activate it
- `pip install flit`
- `flit install`

## Linting and Formatting

Linting and formatting utilizes [ruff](https://github.com/astral-sh/ruff)

- `ruff check`
- `ruff check --select I --fix`
- `ruff format`

## Type Checking

- `mypy applecrate`

## Testing

- `pytest -vv`

## Building

- `rm -rf dist && rm -rf build`
- `flit build`

## Publishing

- `flit publish`

## Updating the README

- `flit install` to install the latest version of the package
- `cog -r README.md` to update the CLI help in README.md

## Updating version

- `bump2version [patch|minor|major] --verbose [--dry-run]`

## Building the Installer Package for AppleCrate, with AppleCrate

- Configuration is in `applecrate.toml`
- Create the x86_64 and arm64 binaries using [pyapp-runner](https://gist.github.com/RhetTbull/7faf1f55350e03cf5ce9f9e4f1ff165e):
  - `pyapp-runner arm applecrate 0.1.4`
  - `pyapp-runner intel applecrate 0.1.4`
- Code sign the binaries
  - `codesign --force --deep --sign $DEVELOPER_ID_APPLICATION applecrate-0.1.4-x86_64`
  - `codesign --force --deep --sign $DEVELOPER_ID_APPLICATION applecrate-0.1.4-arm64`
- `applecrate build`

The installer package uses a post-install script to copy the correct binary for the platform to the correct location.

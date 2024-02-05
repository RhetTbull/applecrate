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

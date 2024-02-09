"""Test applecrate CLI."""

import pathlib
import platform

import pytest
from click.testing import CliRunner

from applecrate.cli import cli
from applecrate.pkg_utils import pkg_files, pkg_info


def test_cli_config_precedence():
    """Test that CLI options override config file options."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("applecrate.toml", "w") as f:
            f.write(
                """
                output = "applecrate_output.pkg"
                app = "applecrate"
                install = [["applecrate.toml", "/usr/local/bin/applecrate.toml"],]
                """
            )
        with open("pyproject.toml", "w") as f:
            f.write(
                """
                [tool.applecrate]
                output = "pyproject_output.pkg"
                version = "2.0.0"
                app = "myapp"
                """
            )
        result = runner.invoke(
            cli,
            [
                "build",
                "--output",
                "{{ app }}-{{ version }}-cli_output.pkg",
            ],
        )
        assert result.exit_code == 0
        assert "applecrate-2.0.0-cli_output.pkg" in result.output
        assert pathlib.Path("applecrate-2.0.0-cli_output.pkg").exists()
        files = pkg_files("applecrate-2.0.0-cli_output.pkg")
        assert "applecrate.pkg/usr/local/bin/applecrate.toml" in files


def test_cli_identifier_machine():
    """Test that the identifier option and machine template work."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "build",
                "--app",
                "myapp",
                "--version",
                "1.0.0",
                "--identifier",
                "com.example.{{ app }}",
                "--output",
                "myapp-{{ machine }}.pkg",
            ],
        )
        assert result.exit_code == 0
        package = pathlib.Path(f"myapp-{platform.machine()}.pkg")
        assert package.exists()
        info = pkg_info(package)
        assert info["identifier"] == "com.example.myapp"

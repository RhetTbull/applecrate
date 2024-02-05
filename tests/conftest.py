"""Test configuration for applecrate"""

import pytest


def write_files(files: dict[str, str]) -> None:
    """Write files to the current directory."""
    for filename, content in files.items():
        with open(filename, "w") as f:
            f.write(content)

"""applecrate: A Python package for creating macOS installer packages."""

from .build import build_installer
from .cli import cli
from .version import __version__

__all__ = ["__version__", "build_installer", "cli"]

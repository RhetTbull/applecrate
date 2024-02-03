"""Utilities for applecrate"""

from __future__ import annotations

import copy
import pathlib
import shutil
from typing import Any

from click import echo


def set_from_defaults(kwargs: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Set values in kwargs from defaults if not provided or set to falsy value.

    Args:
        kwargs: The dictionary of keyword arguments to set.
        defaults: The default values to set if not provided or set to a falsy value.

    Returns: A new dictionary with the updated values.
    """
    updated = copy.deepcopy(kwargs)
    for key, value in defaults.items():
        if key not in updated or not updated[key]:
            updated[key] = value
    return updated


def copy_and_create_parents(src: pathlib.Path, dst: pathlib.Path):
    """Copy a file to a destination and create any necessary parent directories."""
    echo(f"Copying {src} to {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)

"""Utilities for applecrate"""

from __future__ import annotations

import copy
import pathlib
import shutil
import subprocess
from typing import Any, Callable


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


def copy_and_create_parents(src: pathlib.Path, dst: pathlib.Path, verbose: Callable[..., None]):
    """Copy a file to a destination and create any necessary parent directories."""
    verbose(f"Copying {src} to {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)


def check_certificate_is_valid(certificate: str) -> bool:
    """Check if a certificate is valid.

    Args:
        certificate: The certificate to check.

    Returns: True if the certificate is valid, False otherwise.
    """

    status = subprocess.run(["security", "find-identity", "-v"], capture_output=True)
    return certificate in status.stdout.decode("utf-8")

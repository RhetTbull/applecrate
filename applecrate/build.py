"""Build a macOS installer package"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

import click
from click import echo

from .utils import copy_and_create_parents

BUILD_DIR = pathlib.Path("build/applecrate/darwin")
BUILD_ROOT = pathlib.Path("build")


def clean_build_dir(build_dir: pathlib.Path):
    """Clean the build directory."""
    if not build_dir.exists():
        return

    for file in build_dir.iterdir():
        if file.is_file():
            file.unlink()
        else:
            shutil.rmtree(file)


def create_build_dirs(build_dir: pathlib.Path):
    """Create build directory."""

    print(f"Creating build directory {build_dir}")
    # files will be created in the build directory
    build_dir.mkdir(exist_ok=True, parents=True, mode=0o755)

    # Resources contains the welcome and conclusion HTML files
    resources = build_dir / "Resources"
    resources.mkdir(exist_ok=True, mode=0o755)
    echo(f"Created {resources}")

    # scripts contains postinstall and preinstall scripts
    scripts = build_dir / "scripts"
    scripts.mkdir(exist_ok=True, mode=0o755)
    echo(f"Created {scripts}")

    # darwinpkg subdirectory is the root for files to be in installed
    darwinpkg = build_dir / "darwinpkg"
    darwinpkg.mkdir(exist_ok=True, mode=0o755)
    echo(f"Created {darwinpkg}")

    # package subdirectory is the root for the macOS installer package
    package = build_dir / "package"
    package.mkdir(exist_ok=True, mode=0o755)
    echo(f"Created {package}")

    # pkg subdirectory is location of final macOS installer product
    pkg = build_dir / "pkg"
    pkg.mkdir(exist_ok=True, mode=0o755)
    echo(f"Created {pkg}")


def check_dependencies():
    """Check for dependencies."""
    echo("Checking for dependencies.")
    if not shutil.which("pkgbuild"):
        raise click.ClickException("pkgbuild is not installed")
    if not shutil.which("productbuild"):
        raise click.ClickException("productbuild is not installed")
    if not shutil.which("productsign"):
        raise click.ClickException("productsign is not installed")
    if not shutil.which("pkgutil"):
        raise click.ClickException("pkgutil is not installed")


def build_package(app: str, version: str, target_directory: str):
    """Build the macOS installer package."""
    pkg = f"{target_directory}/package/{app}.pkg"
    proc = subprocess.run(
        [
            "pkgbuild",
            "--identifier",
            f"org.{app}.{version}",
            "--version",
            version,
            "--scripts",
            f"{target_directory}/scripts",
            "--root",
            f"{target_directory}/darwinpkg",
            pkg,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise click.ClickException(f"pkgbuild failed: {proc.returncode} {proc.stderr.decode('utf-8')}")
    echo(f"Created {pkg}")


def build_product(app: str, version: str, target_directory: str):
    """Build the macOS installer package."""
    product = f"{target_directory}/pkg/{app}-{version}.pkg"
    proc = subprocess.run(
        [
            "productbuild",
            "--distribution",
            f"{target_directory}/Distribution",
            "--resources",
            f"{target_directory}/Resources",
            "--package-path",
            f"{target_directory}/package",
            product,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise click.ClickException(f"productbuild failed: {proc.returncode} {proc.stderr.decode('utf-8')}")
    echo(f"Created {product}")


def sign_product(
    product_path: str | os.PathLike,
    signed_product_path: str | os.PathLike,
    certificate_id: str,
):
    """Sign the macOS installer package."""
    proc = subprocess.run(
        [
            "productsign",
            "--sign",
            f"Developer ID Installer: {certificate_id}",
            str(product_path),
            str(signed_product_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise click.ClickException(f"productsign failed: {proc.returncode} {proc.stderr.decode('utf-8')}")
    echo(f"Signed {product_path} to {signed_product_path}")

    proc = subprocess.run(
        ["pkgutil", "--check-signature", signed_product_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise click.ClickException(f"pkgutil signature check failed: {proc.returncode} {proc.stderr.decode('utf-8')}")
    echo(f"Checked signature of {signed_product_path}")


def stage_install_files(src: str, dest: str, build_dir: pathlib.Path):
    """Stage install files in the build directory."""
    src = pathlib.Path(src)
    try:
        dest = pathlib.Path(dest).relative_to("/")
    except ValueError:
        dest = pathlib.Path(dest)
    target = build_dir / "darwinpkg" / pathlib.Path(dest)
    if src.is_file():
        copy_and_create_parents(src, target)
    else:
        shutil.copytree(src, target)

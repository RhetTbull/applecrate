"""Build a macOS installer package"""

from __future__ import annotations

import copy
import os
import pathlib
import shutil
import subprocess
from collections.abc import Iterable
from typing import Any, Callable

from jinja2 import Template

from .template_utils import (
    create_html_file,
    get_template,
    render_template,
    render_template_from_file,
)
from .utils import (
    check_certificate_is_valid,
    copy_and_create_parents,
)

BUILD_DIR = pathlib.Path("build/applecrate/darwin")
BUILD_ROOT = pathlib.Path("build")


def build_installer(
    app: str,
    version: str,
    welcome: pathlib.Path | None,
    conclusion: pathlib.Path | None,
    uninstall: pathlib.Path | None,
    no_uninstall: bool,
    url: Iterable[tuple[str, str] | list[str]],
    install: Iterable[tuple[pathlib.Path, pathlib.Path] | list[pathlib.Path]],
    link: Iterable[tuple[pathlib.Path, pathlib.Path] | list[pathlib.Path]],
    license: pathlib.Path,
    banner: pathlib.Path | None,
    post_install: pathlib.Path | None,
    pre_install: pathlib.Path | None,
    sign: str | None,
    verbose: Callable[..., None] | None = None,
):
    """Build a macOS installer package."""
    kwargs = locals()
    validate_build_kwargs(**kwargs)

    if not verbose:

        def verbose(*args, **kwargs):
            pass

    # render templates in kwargs (e.g. for --install)
    kwargs = render_build_kwargs(kwargs)

    app = kwargs["app"]
    version = kwargs["version"]
    welcome = kwargs["welcome"]
    conclusion = kwargs["conclusion"]
    uninstall = kwargs["uninstall"]
    no_uninstall = kwargs["no_uninstall"]
    url = kwargs["url"]
    install = kwargs["install"]
    link = kwargs["link"]
    license = kwargs["license"]
    banner = kwargs["banner"]
    post_install = kwargs["post_install"]
    pre_install = kwargs["pre_install"]
    sign = kwargs["sign"]

    # template data
    data: dict[str, Any] = {
        "app": app,
        "version": version,
        "uninstall": not no_uninstall,
        "url": url,
        "install": install,
        "banner": banner,
        "link": link,
        "post_install": post_install,
        "pre_install": pre_install,
    }

    verbose(f"Building installer package for {app} version {version}.")

    verbose("Cleaning build directory")
    clean_build_dir(BUILD_DIR)
    verbose("Creating build directories")
    create_build_dirs(BUILD_DIR, verbose=verbose)

    # Render the welcome and conclusion templates
    verbose("Creating welcome.html")
    create_html_file(
        welcome,
        BUILD_DIR / "Resources" / "welcome.html",
        data,
        "welcome.md",
        verbose=verbose,
    )

    verbose("Creating conclusion.html")
    create_html_file(
        conclusion,
        BUILD_DIR / "Resources" / "conclusion.html",
        data,
        "conclusion.md",
        verbose=verbose,
    )

    verbose("Copying license file")
    copy_and_create_parents(
        license, BUILD_DIR / "Resources" / "LICENSE.txt", verbose=verbose
    )

    verbose("Copying install files")
    for src, dst in install:
        stage_install_files(src, dst, BUILD_DIR, verbose=verbose)

    # Render the uninstall script
    if not no_uninstall:
        verbose("Creating uninstall script")
        target = (
            BUILD_DIR
            / "darwinpkg"
            / "Library"
            / "Application Support"
            / app
            / version
            / "uninstall.sh"
        )
        if uninstall:
            render_template_from_file(uninstall, data, target)
        else:
            template = get_template("uninstall.sh")
            render_template(template, data, target)
        pathlib.Path(target).chmod(0o755)
        verbose(f"Created {target}")

    verbose("Creating pre- and post-install scripts")

    target = BUILD_DIR / "scripts" / "preinstall"
    template = get_template("preinstall")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    verbose(f"Created {target}")

    target = BUILD_DIR / "scripts" / "postinstall"
    template = get_template("postinstall")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    verbose(f"Created {target}")

    target = BUILD_DIR / "scripts" / "links"
    template = get_template("links")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    verbose(f"Created {target}")

    if pre_install:
        target = BUILD_DIR / "scripts" / "custom_preinstall"
        render_template_from_file(pre_install, data, target)
        pathlib.Path(target).chmod(0o755)
        verbose(f"Created {target}")

    if post_install:
        target = BUILD_DIR / "scripts" / "custom_postinstall"
        render_template_from_file(post_install, data, target)
        pathlib.Path(target).chmod(0o755)
        verbose(f"Created {target}")

    if banner:
        verbose("Copying banner image")
        target = BUILD_DIR / "Resources" / "banner.png"
        copy_and_create_parents(banner, target, verbose=verbose)
        verbose(f"Created {target}")

    verbose("Creating distribution file")
    target = BUILD_DIR / "Distribution"
    template = get_template("Distribution")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    verbose(f"Created {target}")

    # Build the macOS installer package
    verbose("Building the macOS installer package")
    build_package(app, version, BUILD_DIR, verbose=verbose)

    # Build the macOS installer product
    verbose("Building the macOS installer product")
    build_product(app, version, BUILD_DIR, verbose=verbose)
    product = f"{app}-{version}.pkg"
    product_path = BUILD_DIR / "pkg" / product

    # sign the installer package
    if sign:
        signed_product_path = BUILD_DIR / "pkg-signed" / f"{app}-{version}.pkg"
        signed_product_path.parent.mkdir(parents=True, exist_ok=True)
        verbose(f"Signing the installer package with certificate ID: {sign}")
        sign_product(product_path, signed_product_path, sign, verbose=verbose)

    verbose("Copying installer package to build directory")
    product_path = product_path if not sign else signed_product_path
    shutil.copy(product_path, BUILD_ROOT / product)

    verbose(f"Created {BUILD_ROOT / product}")
    verbose("Done!")


def render_build_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Render template variables in kwargs."""
    rendered = copy.deepcopy(kwargs)
    app = kwargs["app"]
    version = kwargs["version"]
    if install := rendered.get("install"):
        new_install = []
        for src, dest in install:
            template = Template(str(dest))
            dest = pathlib.Path(template.render(app=app, version=version))
            new_install.append((src, dest))
        rendered["install"] = new_install

    if link := rendered.get("link"):
        new_link = []
        for src, target in link:
            src_template = Template(str(src))
            target_template = Template(str(target))
            src = pathlib.Path(src_template.render(app=app, version=version))
            target = pathlib.Path(target_template.render(app=app, version=version))
            new_link.append((src, target))
        rendered["link"] = new_link
    return rendered


def validate_build_kwargs(**kwargs):
    """Validate the build command arguments."""

    # version and app must be provided
    if not kwargs.get("app"):
        raise ValueError("App name must be provided")

    if not kwargs.get("version"):
        raise ValueError("Version must be provided")

    if not kwargs.get("license"):
        raise ValueError("License file must be provided")
    kwargs["license"] = pathlib.Path(kwargs["license"])

    if kwargs.get("no_uninstall") and kwargs.get("uninstall"):
        raise ValueError("Cannot specify both --uninstall and --no-uninstall")

    if welcome := kwargs.get("welcome"):
        welcome = pathlib.Path(welcome)
        if welcome.suffix.lower() not in [".md", ".markdown", ".html"]:
            raise ValueError("Welcome file must be a markdown or HTML file")
        kwargs["welcome"] = welcome

    if conclusion := kwargs.get("conclusion"):
        conclusion = pathlib.Path(conclusion)
        if conclusion.suffix.lower() not in [".md", ".markdown", ".html"]:
            raise ValueError("Conclusion file must be a markdown or HTML file")
        kwargs["conclusion"] = conclusion

    if uninstall := kwargs.get("uninstall"):
        uninstall = pathlib.Path(uninstall)
        if uninstall.suffix.lower() != ".sh":
            raise ValueError("Uninstall script must be a shell script")
        kwargs["uninstall"] = uninstall

    if install := kwargs.get("install"):
        pathlib_install = []
        for src, dest in install:
            src = pathlib.Path(src)
            if not src.exists():
                raise ValueError(f"Install dir/file {src} does not exist")
            dest = pathlib.Path(dest)
            if not dest.is_absolute():
                raise ValueError(f"Install destination {dest} must be an absolute path")
            pathlib_install.append((src, dest))
        kwargs["install"] = pathlib_install

    if link := kwargs.get("link"):
        pathlib_link = []
        for src, target in link:
            src = pathlib.Path(src)
            target = pathlib.Path(target)
            if not src.is_absolute():
                raise ValueError(f"Link source {src} must be an absolute path")
            if not target.is_absolute():
                raise ValueError(f"Link target {target} must be an absolute path")
            pathlib_link.append((src, target))
        kwargs["link"] = pathlib_link

    if banner := kwargs.get("banner"):
        banner = pathlib.Path(banner)
        if banner.suffix.lower() != ".png":
            raise ValueError("Banner image must be a PNG file")
        kwargs["banner"] = banner

    if sign := kwargs.get("sign"):
        if sign.startswith("Developer ID Installer:"):
            sign = sign[23:]
        if sign.startswith("$"):
            # get the value of the environment variable
            sign = os.environ.get(sign[1:])
            if not sign:
                raise ValueError(f"Environment variable {sign[1:]} is not set")
        if not check_certificate_is_valid(sign):
            raise ValueError(f"Invalid certificate ID: {sign}")
        kwargs["sign"] = sign


def clean_build_dir(build_dir: pathlib.Path):
    """Clean the build directory."""
    if not build_dir.exists():
        return

    for file in build_dir.iterdir():
        if file.is_file():
            file.unlink()
        else:
            shutil.rmtree(file)


def create_build_dirs(build_dir: pathlib.Path, verbose: Callable[..., None]):
    """Create build directory."""

    print(f"Creating build directory {build_dir}")
    # files will be created in the build directory
    build_dir.mkdir(exist_ok=True, parents=True, mode=0o755)

    # Resources contains the welcome and conclusion HTML files
    resources = build_dir / "Resources"
    resources.mkdir(exist_ok=True, mode=0o755)
    verbose(f"Created {resources}")

    # scripts contains postinstall and preinstall scripts
    scripts = build_dir / "scripts"
    scripts.mkdir(exist_ok=True, mode=0o755)
    verbose(f"Created {scripts}")

    # darwinpkg subdirectory is the root for files to be in installed
    darwinpkg = build_dir / "darwinpkg"
    darwinpkg.mkdir(exist_ok=True, mode=0o755)
    verbose(f"Created {darwinpkg}")

    # package subdirectory is the root for the macOS installer package
    package = build_dir / "package"
    package.mkdir(exist_ok=True, mode=0o755)
    verbose(f"Created {package}")

    # pkg subdirectory is location of final macOS installer product
    pkg = build_dir / "pkg"
    pkg.mkdir(exist_ok=True, mode=0o755)
    verbose(f"Created {pkg}")


def check_dependencies(verbose: Callable[..., None]):
    """Check for dependencies."""
    verbose("Checking for dependencies.")
    if not shutil.which("pkgbuild"):
        raise FileNotFoundError("pkgbuild is not installed")
    if not shutil.which("productbuild"):
        raise FileNotFoundError("productbuild is not installed")
    if not shutil.which("productsign"):
        raise FileNotFoundError("productsign is not installed")
    if not shutil.which("pkgutil"):
        raise FileNotFoundError("pkgutil is not installed")


def build_package(
    app: str, version: str, target_directory: pathlib.Path, verbose: Callable[..., None]
):
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
        raise RuntimeError(
            f"pkgbuild failed: {proc.returncode} {proc.stderr.decode('utf-8')}"
        )
    verbose(f"Created {pkg}")


def build_product(
    app: str, version: str, target_directory: pathlib.Path, verbose: Callable[..., None]
):
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
        raise RuntimeError(
            f"productbuild failed: {proc.returncode} {proc.stderr.decode('utf-8')}"
        )
    verbose(f"Created {product}")


def sign_product(
    product_path: str | os.PathLike,
    signed_product_path: str | os.PathLike,
    certificate_id: str,
    verbose: Callable[..., None],
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
        raise RuntimeError(
            f"productsign failed: {proc.returncode} {proc.stderr.decode('utf-8')}"
        )
    verbose(f"Signed {product_path} to {signed_product_path}")

    proc = subprocess.run(
        ["pkgutil", "--check-signature", signed_product_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"pkgutil signature check failed: {proc.returncode} {proc.stderr.decode('utf-8')}"
        )
    verbose(f"Checked signature of {signed_product_path}")


def stage_install_files(
    src: pathlib.Path,
    dest: pathlib.Path,
    build_dir: pathlib.Path,
    verbose: Callable[..., None],
):
    """Stage install files in the build directory."""
    try:
        dest = pathlib.Path(dest).relative_to("/")
    except ValueError:
        pass
    target = build_dir / "darwinpkg" / dest
    if src.is_file():
        copy_and_create_parents(src, target, verbose=verbose)
    else:
        shutil.copytree(src, target)

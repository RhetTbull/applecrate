"""Build a macOS installer package"""

from __future__ import annotations

import os
import pathlib
import platform
import shutil
import subprocess
from collections.abc import Iterable
from typing import Any, Callable

from .template_utils import (
    create_html_file,
    get_template,
    render_path,
    render_path_list_of_tuple,
    render_str,
    render_template,
    render_template_from_file,
)
from .utils import check_certificate_is_valid, copy_and_create_parents

BUILD_DIR = pathlib.Path("build/applecrate/darwin")
BUILD_ROOT = pathlib.Path("build")


def no_op(*args, **kwargs):
    pass


def build_installer(
    app: str,
    version: str,
    identifier: str | None = None,
    welcome: str | os.PathLike | None = None,
    conclusion: str | os.PathLike | None = None,
    uninstall: str | os.PathLike | None = None,
    no_uninstall: bool = False,
    url: Iterable[tuple[str, str] | list[str]] | None = None,
    install: (Iterable[tuple[str | os.PathLike, str | os.PathLike] | list[str | os.PathLike]] | None) = None,
    link: (Iterable[tuple[str | os.PathLike, str | os.PathLike] | list[str | os.PathLike]] | None) = None,
    license: str | os.PathLike | None = None,
    banner: str | os.PathLike | None = None,
    post_install: str | os.PathLike | None = None,
    pre_install: str | os.PathLike | None = None,
    chmod: (Iterable[tuple[str | int, str | os.PathLike] | list[str | int | str | os.PathLike]] | None) = None,
    sign: str | None = None,
    output: str | os.PathLike | None = None,
    build_dir: str | os.PathLike | None = None,
    verbose: Callable[..., None] = no_op,
):
    """Build a macOS installer package.

    Args:
        app: The name of the app.
        version: The version of the app.
        identifier: The package identifier. If not provided, it will be generated from the app name.
        welcome: The path to the welcome markdown or HTML file.
        conclusion: The path to the conclusion markdown or HTML file.
        uninstall: The path to the uninstall shell script.
        no_uninstall: If True, do not include an uninstall script.
        url: A list of URLs to include in the installer package.
        install: A list of tuples of source and destination paths to install.
        link: A list of tuples of source and target paths to create symlinks.
        license: The path to the license file. If provided, it will be copied to the installer package and user will be prompted to accept it.
        banner: The path to the banner image.
        post_install: The path to the post-install shell script. If provided, will be run after other post-install actions such as links and chmod.
        pre_install: The path to the pre-install shell script.
        sign: The certificate ID to sign the installer package.
        chmod: A list of tuples of mode and path to change the mode of files in the installer package.
        output: The path to the installer package; if not provided, the package will be created in the build directory.
        build_dir: The build directory; default is BUILD_DIR.
        verbose: An optional function to print verbose output.

    Note: The welcome, conclusion, uninstall, post_install, and pre_install files
    will be rendered as Jinja2 templates.
    The welcome and conclusion files may be in Markdown or HTML format.
    If in Markdown format, they will be converted to HTML.
    The paths for install target, link target, build_dir, and output will
    also be rendered as Jinja2 templates. For example:
    output = "{{ app }}-{{ version }}.pkg"

    The Jinja2 template variables available are:

    - app: The name of the app.
    - version: The version of the app.
    - identifier: The package identifier.
    - uninstall: The path to the uninstall shell script.
    - url: A list of URLs to include in the installer package.
    - install: A list of tuples of source and destination paths to install.
    - banner: The path to the banner image.
    - link: A list of tuples of source and target paths to create symlinks.
    - post_install: The path to the post-install shell script.
    - pre_install: The path to the pre-install shell script.
    - chmod: A list of tuples of mode and path to change the mode of files post-installation.
    - build_dir: The build directory.
    - output: The path to the installer package.
    - machine: the platform.machine() value, e.g. 'x86_64' or 'arm64'

    """

    # validate arguments and perform necessary conversions (e.g. str to pathlib.Path)
    app = validate_app(app)
    version = validate_version(version)
    identifier = identifier or "org.opensource.{{ app }}"
    welcome = validate_optional_path_extension(welcome, "welcome", [".md", ".html"])
    conclusion = validate_optional_path_extension(conclusion, "conclusion", [".md", ".html"])
    uninstall = validate_optional_path_extension(uninstall, "uninstall", [".sh"])
    if uninstall and no_uninstall:
        raise ValueError("Cannot specify both --uninstall and --no-uninstall")
    install = validate_install(install, {"app": app, "version": version, "machine": platform.machine()})
    link = validate_link(link)
    license = validate_optional_path_exists(license, "license")
    banner = validate_optional_path_extension(banner, "banner", [".png"])
    post_install = validate_optional_path_extension(post_install, "post_install", [".sh"])
    pre_install = validate_optional_path_extension(pre_install, "pre_install", [".sh"])
    sign = validate_sign(sign)
    output = validate_optional_path_parent_exists(output, "output")
    build_dir = validate_optional_path_exists(build_dir, "build_dir") or BUILD_DIR
    chmod = validate_chmod(chmod)

    # template data
    data: dict[str, Any] = {
        "app": app,
        "version": version,
        "identifier": identifier,
        "uninstall": not no_uninstall,
        "url": url,
        "install": install,
        "banner": banner,
        "link": link,
        "post_install": post_install,
        "pre_install": pre_install,
        "chmod": chmod,
        "build_dir": build_dir,
        "output": output,
        "machine": platform.machine(),
    }

    # render args that accept templates and update data
    identifier = render_str(identifier, data)
    data["identifier"] = identifier
    output = render_path(output, data) if output else None
    data["output"] = output
    build_dir = render_path(build_dir, data)
    data["build_dir"] = build_dir
    install = render_path_list_of_tuple(install, data)
    data["install"] = install
    link = render_path_list_of_tuple(link, data)
    data["link"] = link

    build_installer_(
        app=app,
        version=version,
        identifier=identifier,
        welcome=welcome,
        conclusion=conclusion,
        uninstall=uninstall,
        no_uninstall=no_uninstall,
        install=install,
        license=license,
        banner=banner,
        post_install=post_install,
        pre_install=pre_install,
        sign=sign,
        output=output,
        build_dir=build_dir,
        verbose=verbose,
        data=data,
    )


def build_installer_(
    app: str,
    version: str,
    identifier: str,
    welcome: pathlib.Path | None = None,
    conclusion: pathlib.Path | None = None,
    uninstall: pathlib.Path | None = None,
    no_uninstall: bool = False,
    install: Iterable[tuple[pathlib.Path, pathlib.Path]] | None = None,
    license: pathlib.Path | None = None,
    banner: pathlib.Path | None = None,
    post_install: pathlib.Path | None = None,
    pre_install: pathlib.Path | None = None,
    sign: str | None = None,
    output: pathlib.Path | None = None,
    build_dir: pathlib.Path | None = None,
    verbose: Callable[..., None] = no_op,
    data: dict[str, Any] = {},
):
    verbose(f"Building installer package for {app} version {version}.")

    build_dir = build_dir / "applecrate" / "darwin" if build_dir else BUILD_DIR
    verbose(f"Cleaning build directory: {build_dir}")
    clean_build_dir(build_dir)
    verbose("Creating build directories")
    create_build_dirs(build_dir, verbose=verbose)

    # Render the welcome and conclusion templates
    verbose("Creating welcome.html")
    create_html_file(
        welcome,
        build_dir / "Resources" / "welcome.html",
        data,
        "welcome.md",
        verbose=verbose,
    )

    verbose("Creating conclusion.html")
    create_html_file(
        conclusion,
        build_dir / "Resources" / "conclusion.html",
        data,
        "conclusion.md",
        verbose=verbose,
    )

    if license:
        verbose("Copying license file")
        copy_and_create_parents(license, build_dir / "Resources" / "LICENSE.txt", verbose=verbose)

    if install:
        verbose("Copying install files")
        for src, dst in install:
            stage_install_files(src, dst, build_dir, verbose=verbose)

    # Render the uninstall script
    if not no_uninstall:
        verbose("Creating uninstall script")
        target = build_dir / "darwinpkg" / "Library" / "Application Support" / app / version / "uninstall.sh"
        if uninstall:
            render_template_from_file(uninstall, data, target)
        else:
            template = get_template("uninstall.sh")
            render_template(template, data, target)
        pathlib.Path(target).chmod(0o755)
        verbose(f"Created {target}")

    verbose("Creating pre- and post-install scripts")

    target = build_dir / "scripts" / "preinstall"
    template = get_template("preinstall")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    verbose(f"Created {target}")

    target = build_dir / "scripts" / "postinstall"
    template = get_template("postinstall")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    verbose(f"Created {target}")

    if pre_install:
        target = build_dir / "scripts" / "custom_preinstall"
        render_template_from_file(pre_install, data, target)
        pathlib.Path(target).chmod(0o755)
        verbose(f"Created {target}")

    if post_install:
        target = build_dir / "scripts" / "custom_postinstall"
        render_template_from_file(post_install, data, target)
        pathlib.Path(target).chmod(0o755)
        verbose(f"Created {target}")

    if banner:
        verbose("Copying banner image")
        target = build_dir / "Resources" / "banner.png"
        copy_and_create_parents(banner, target, verbose=verbose)
        verbose(f"Created {target}")

    verbose("Creating distribution file")
    target = build_dir / "Distribution"
    template = get_template("Distribution")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    verbose(f"Created {target}")

    # Build the macOS installer package
    verbose("Building the macOS installer package")
    build_package(app, version, identifier, build_dir, verbose=verbose)

    # Build the macOS installer product
    verbose("Building the macOS installer product")
    build_product(app, version, build_dir, verbose=verbose)
    product = f"{app}-{version}.pkg"
    product_path = build_dir / "pkg" / product

    # sign the installer package
    if sign:
        signed_product_path = build_dir / "pkg-signed" / f"{app}-{version}.pkg"
        signed_product_path.parent.mkdir(parents=True, exist_ok=True)
        verbose(f"Signing the installer package with certificate ID: {sign}")
        sign_product(product_path, signed_product_path, sign, verbose=verbose)

    product_path = product_path if not sign else signed_product_path
    target_path = output or BUILD_ROOT / product
    verbose(f"Copying installer package to target: {target_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(product_path, target_path)

    verbose(f"Created {target_path}")
    verbose("Done!")


def validate_app(app: str) -> str:
    """Validate build_installer app argument."""
    if not app:
        raise ValueError("App name must be provided")
    return app


def validate_version(version: str) -> str:
    """Validate build_installer version argument."""
    if not version:
        raise ValueError("Version must be provided")
    return version


def validate_optional_path_exists(arg: str | os.PathLike | None, name: str) -> pathlib.Path | None:
    """Validate an optional path argument."""
    if not arg:
        return None
    path = pathlib.Path(arg)
    if not path.exists():
        raise FileNotFoundError(f"{name}: {path} does not exist")
    return path


def validate_optional_path_parent_exists(arg: str | os.PathLike | None, name: str) -> pathlib.Path | None:
    """Validate an optional path argument."""
    if not arg:
        return None
    path = pathlib.Path(arg)
    if not path.parent.exists():
        raise ValueError(f"{name}: parent {path.parent} does not exist")
    return path


def validate_optional_path_extension(path: str | os.PathLike | None, name: str, extension: list[str]) -> pathlib.Path | None:
    """Validate argument is a valid path with a given extension, or None."""
    path = validate_optional_path_exists(path, name)
    if not path:
        return None
    if path.suffix.lower() not in extension:
        raise ValueError(f"{name} must be a valid path with extension: {extension}")
    return path


def validate_install(
    install: (Iterable[tuple[str | os.PathLike, str | os.PathLike] | list[str | os.PathLike]] | None),
    data: dict[str, Any],
) -> list[tuple[pathlib.Path, pathlib.Path]]:
    """Validate build_installer install argument."""
    if not install:
        return []
    pathlib_install = []
    for src, dest in install:
        src = pathlib.Path(src)
        src = render_path(src, data)
        if not src.exists():
            raise ValueError(f"Install dir/file {src} does not exist")
        dest = pathlib.Path(dest)
        if not dest.is_absolute():
            raise ValueError(f"Install destination {dest} must be an absolute path")
        pathlib_install.append((src, dest))
    return pathlib_install


def validate_link(
    link: (Iterable[tuple[str | os.PathLike, str | os.PathLike] | list[str | os.PathLike]] | None),
) -> list[tuple[pathlib.Path, pathlib.Path]]:
    if not link:
        return []
    pathlib_link = []
    for src, target in link:
        src = pathlib.Path(src)
        target = pathlib.Path(target)
        if not src.is_absolute():
            raise ValueError(f"Link source {src} must be an absolute path")
        if not target.is_absolute():
            raise ValueError(f"Link target {target} must be an absolute path")
        pathlib_link.append((src, target))
    return pathlib_link


def validate_sign(sign: str | None) -> str | None:
    """Validate the sign argument."""
    if not sign:
        return None
    if sign.startswith("$"):
        # get the value of the environment variable
        env_sign = os.environ.get(sign[1:])
        if not env_sign:
            raise ValueError(f"Environment variable {sign[1:]} is not set")
        sign = env_sign
    if sign.startswith("Developer ID Installer:"):
        sign = sign[24:]
    if not check_certificate_is_valid(sign):
        raise ValueError(f"Invalid certificate ID: {sign}")
    return sign


def validate_chmod(
    chmod: (Iterable[tuple[str | int, str | os.PathLike] | list[str | int | str | os.PathLike]] | None),
) -> list[tuple[str, pathlib.Path]] | None:
    """Validate chmod argument."""
    if not chmod:
        return None
    new_chmod = []
    for mode, path in chmod:
        path = pathlib.Path(str(path))
        mode = str(mode)  # mode may be an int or a str representing an octal number
        if not path.is_absolute():
            raise ValueError(f"Chmod path {path} must be an absolute path")
        if not mode.isdigit():
            raise ValueError(f"Chmod mode {mode} must be an octal number")
        # mode must be 3 or 4 octal digits
        if len(mode) not in [3, 4]:
            raise ValueError(f"Chmod mode {mode} must be 3 or 4 octal digits")
        new_chmod.append((mode, path))
    return new_chmod


def validate_build_kwargs(**kwargs) -> dict[str, Any]:
    """Validate the build command arguments for CLI"""

    # version and app must be provided
    if not kwargs.get("app"):
        raise ValueError("App name must be provided")

    if not kwargs.get("version"):
        raise ValueError("Version must be provided")

    if license := kwargs.get("license"):
        kwargs["license"] = validate_optional_path_exists(license, "license")

    if kwargs.get("no_uninstall") and kwargs.get("uninstall"):
        raise ValueError("Cannot specify both --uninstall and --no-uninstall")

    if welcome := kwargs.get("welcome"):
        kwargs["welcome"] = validate_optional_path_extension(welcome, "welcome", [".md", ".html"])

    if conclusion := kwargs.get("conclusion"):
        kwargs["conclusion"] = validate_optional_path_extension(conclusion, "conclusion", [".md", ".html"])

    if uninstall := kwargs.get("uninstall"):
        kwargs["uninstall"] = validate_optional_path_extension(uninstall, "uninstall", [".sh"])

    if install := kwargs.get("install"):
        # install needs to be rendered to ensure paths exists
        data = {
            "app": kwargs.get("app"),
            "version": kwargs.get("version"),
            "machine": platform.machine(),
        }
        kwargs["install"] = validate_install(install, data)

    if link := kwargs.get("link"):
        kwargs["link"] = validate_link(link)

    if banner := kwargs.get("banner"):
        kwargs["banner"] = validate_optional_path_extension(banner, "banner", [".png"])

    if sign := kwargs.get("sign"):
        kwargs["sign"] = validate_sign(sign)

    if build_dir := kwargs.get("build_dir"):
        kwargs["build_dir"] = validate_optional_path_exists(build_dir, "build_dir")

    if output := kwargs.get("output"):
        kwargs["output"] = validate_optional_path_parent_exists(output, "output")

    if chmod := kwargs.get("chmod"):
        kwargs["chmod"] = validate_chmod(chmod)

    return kwargs


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

    verbose(f"Creating build directory {build_dir}")
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
    app: str,
    version: str,
    identifier: str,
    target_directory: pathlib.Path,
    verbose: Callable[..., None],
):
    """Build the macOS installer package."""
    pkg = f"{target_directory}/package/{app}.pkg"
    proc = subprocess.run(
        [
            "pkgbuild",
            "--identifier",
            identifier,
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
        raise RuntimeError(f"pkgbuild failed: {proc.returncode} {proc.stderr.decode('utf-8')}")
    verbose(f"Created {pkg}")


def build_product(app: str, version: str, target_directory: pathlib.Path, verbose: Callable[..., None]):
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
        raise RuntimeError(f"productbuild failed: {proc.returncode} {proc.stderr.decode('utf-8')}")
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
        raise RuntimeError(f"productsign failed: {proc.returncode} {proc.stderr.decode('utf-8')}")
    verbose(f"Signed {product_path} to {signed_product_path}")

    proc = subprocess.run(
        ["pkgutil", "--check-signature", signed_product_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pkgutil signature check failed: {proc.returncode} {proc.stderr.decode('utf-8')}")
    verbose(f"Checked signature of {signed_product_path}")


def stage_install_files(
    src: str | os.PathLike,
    dest: str | os.PathLike,
    build_dir: str | os.PathLike,
    verbose: Callable[..., None],
):
    """Stage install files in the build directory."""
    src = pathlib.Path(src)
    dest = pathlib.Path(dest)
    build_dir = pathlib.Path(build_dir)
    try:
        dest = pathlib.Path(dest).relative_to("/")
    except ValueError:
        pass
    target = build_dir / "darwinpkg" / dest
    if src.is_file():
        copy_and_create_parents(src, target, verbose=verbose)
    else:
        shutil.copytree(src, target)

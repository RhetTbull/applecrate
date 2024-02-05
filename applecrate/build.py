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
from .utils import check_certificate_is_valid, copy_and_create_parents

BUILD_DIR = pathlib.Path("build/applecrate/darwin")
BUILD_ROOT = pathlib.Path("build")


def build_installer(
    app: str,
    version: str,
    welcome: pathlib.Path | None = None,
    conclusion: pathlib.Path | None = None,
    uninstall: pathlib.Path | None = None,
    no_uninstall: bool = False,
    url: Iterable[tuple[str, str] | list[str]] | None = None,
    install: (Iterable[tuple[pathlib.Path, pathlib.Path] | list[pathlib.Path]] | None) = None,
    link: (Iterable[tuple[pathlib.Path, pathlib.Path] | list[pathlib.Path]] | None) = None,
    license: pathlib.Path | None = None,
    banner: pathlib.Path | None = None,
    post_install: pathlib.Path | None = None,
    pre_install: pathlib.Path | None = None,
    chmod: (Iterable[tuple[str | int, pathlib.Path] | list[str | int | pathlib.Path]] | None) = None,
    sign: str | None = None,
    output: pathlib.Path | None = None,
    build_dir: pathlib.Path | None = None,
    verbose: Callable[..., None] | None = None,
):
    """Build a macOS installer package.

    Args:
        app: The name of the app.
        version: The version of the app.
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

    """
    kwargs = validate_build_kwargs(**locals())

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
    output = kwargs["output"]
    build_dir = kwargs["build_dir"]
    chmod = kwargs["chmod"]

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
        "chmod": chmod,
        "build_dir": build_dir,
        "output": output,
    }

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
    build_package(app, version, build_dir, verbose=verbose)

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

    if build_dir := rendered.get("build_dir"):
        template = Template(str(build_dir))
        rendered["build_dir"] = pathlib.Path(template.render(app=app, version=version))

    if output := rendered.get("output"):
        template = Template(str(output))
        rendered["output"] = pathlib.Path(template.render(app=app, version=version))

    return rendered


def validate_build_kwargs(**kwargs) -> dict[str, Any]:
    """Validate the build command arguments."""

    # version and app must be provided
    if not kwargs.get("app"):
        raise ValueError("App name must be provided")

    if not kwargs.get("version"):
        raise ValueError("Version must be provided")

    if kwargs.get("license"):
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

    if build_dir := kwargs.get("build_dir"):
        kwargs["build_dir"] = pathlib.Path(build_dir)

    if output := kwargs.get("output"):
        kwargs["output"] = pathlib.Path(output)

    if chmod := kwargs.get("chmod"):
        new_chmod = []
        for mode, path in chmod:
            path = pathlib.Path(path)
            mode = str(mode)  # mode may be an int or a str representing an octal number
            if not path.is_absolute():
                raise ValueError(f"Chmod path {path} must be an absolute path")
            if not mode.isdigit():
                raise ValueError(f"Chmod mode {mode} must be an octal number")
            # mode must be 3 or 4 octal digits
            if len(mode) not in [3, 4]:
                raise ValueError(f"Chmod mode {mode} must be 3 or 4 octal digits")
            new_chmod.append((mode, path))
        kwargs["chmod"] = new_chmod

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


def build_package(app: str, version: str, target_directory: pathlib.Path, verbose: Callable[..., None]):
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

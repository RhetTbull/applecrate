"""CLI for applecrate to build macOS installer packages."""

from __future__ import annotations

import copy
import os
import pathlib
from typing import Any

import click
import toml
from click import echo
from jinja2 import Template

from .build import (
    BUILD_DIR,
    build_package,
    build_product,
    check_dependencies,
    clean_build_dir,
    create_build_dirs,
    stage_install_files,
)
from .template_utils import create_html_file, get_template, render_template
from .utils import copy_and_create_parents, set_from_defaults


@click.group()
def cli():
    """applecrate: A Python package for creating macOS installer packages."""
    pass


# @cli.command()
# def init():
#     """Create a new applecrate project."""
#     echo("Creating a new applecrate project.")


# @cli.command()
# def check():
#     """Check the current environment for applecrate."""
#     echo("Checking the current environment for applecrate.")


@cli.command()
@click.option("--app", "-a", help="App name")
@click.option("--version", "-v", help="App version")
@click.option(
    "--license",
    "-l",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to license file",
)
@click.option(
    "--welcome",
    "-w",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to welcome markdown or HTML file",
)
@click.option(
    "--conclusion",
    "-c",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to conclusion markdown or HTML file",
)
@click.option(
    "--uninstall",
    "-u",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to uninstall script; "
    "if not provided, an uninstall script will be created for you."
    "See also '--no-uninstall'",
)
@click.option(
    "--no-uninstall",
    "-U",
    is_flag=True,
    help="Do not include an uninstall script in the package",
)
@click.option(
    "--url",
    "-L",
    metavar="NAME URL",
    multiple=True,
    nargs=2,
    help="Links to additional resources to include in conclusion HTML shown after installation. "
    "For example, the project website or documentation.",
)
@click.option(
    "--banner",
    "-b",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to optional PNG banner image for installer package.",
)
@click.option(
    "--install",
    "-i",
    metavar="FILE_OR_DIR DEST",
    nargs=2,
    multiple=True,
    help="Install FILE_OR_DIR to destination DEST; "
    "DEST must be an absolute path, for example '/usr/local/bin/app'. "
    r"DEST may include template variables {{ app }} and {{ version }}. "
    'For example: `--install dist/app "/usr/local/bin/{{ app }}-{{ version }}"` '
    "will install the file 'dist/app' to '/usr/local/bin/app-1.0.0' "
    "if --app=app and --version=1.0.0.",
)
@click.option(
    "--link",
    "-k",
    metavar="SRC TARGET",
    nargs=2,
    multiple=True,
    help="Create a symbolic link from SRC to DEST after installation. "
    "SRC and TARGET must be absolute paths and both may include template variables {{ app }} and {{ version }}. "
    'For example: `--link "/Library/Application Support/{{ app }}/{{ version }}/app" "/usr/local/bin/{{ app }}-{{ version }}"` ',
)
@click.option(
    "--pre-install",
    "-p",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to pre-install shell script; "
    "if not provided, a pre-install script will be created for you.",
)
@click.option(
    "--post-install",
    "-P",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to post-install shell script; "
    "if not provided, a post-install script will be created for you.",
)
def build(**kwargs):
    """applecrate: A Python package for creating macOS installer packages."""

    check_dependencies()

    # If both pyproject.toml and command line options are provided,
    # the command line options take precedence
    toml_kwargs = load_from_toml("pyproject.toml")
    kwargs = set_from_defaults(kwargs, toml_kwargs)

    try:
        validate_build_kwargs(**kwargs)
    except ValueError as e:
        raise click.BadParameter(str(e))

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

    # template data
    data = {
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

    echo(f"Building installer package for {app} version {version}.")

    echo("Cleaning build directory")
    clean_build_dir(BUILD_DIR)
    echo("Creating build directories")
    create_build_dirs(BUILD_DIR)

    # Render the welcome and conclusion templates
    echo("Creating welcome.html")
    create_html_file(
        welcome, BUILD_DIR / "Resources" / "welcome.html", data, "welcome.md"
    )
    echo("Creating conclusion.html")
    create_html_file(
        conclusion, BUILD_DIR / "Resources" / "conclusion.html", data, "conclusion.md"
    )

    echo("Copying license file")
    copy_and_create_parents(license, BUILD_DIR / "Resources" / "LICENSE.txt")

    echo("Copying install files")
    for src, dst in install:
        stage_install_files(src, dst, BUILD_DIR)

    # Render the uninstall script
    if not no_uninstall:
        echo("Creating uninstall script")
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
            copy_and_create_parents(uninstall, target)
        else:
            template = get_template("uninstall.sh")
            render_template(template, data, target)
        pathlib.Path(target).chmod(0o755)
        echo(f"Created {target}")

    echo("Creating pre- and post-install scripts")

    target = BUILD_DIR / "scripts" / "preinstall"
    template = get_template("preinstall")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    echo(f"Created {target}")

    target = BUILD_DIR / "scripts" / "postinstall"
    template = get_template("postinstall")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    echo(f"Created {target}")

    target = BUILD_DIR / "scripts" / "links"
    template = get_template("links")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    echo(f"Created {target}")

    if pre_install:
        target = BUILD_DIR / "scripts" / "custom_preinstall"
        copy_and_create_parents(pre_install, target)
        pathlib.Path(target).chmod(0o755)
        echo(f"Created {target}")

    if post_install:
        target = BUILD_DIR / "scripts" / "custom_postinstall"
        copy_and_create_parents(post_install, target)
        pathlib.Path(target).chmod(0o755)
        echo(f"Created {target}")

    if banner:
        echo("Copying banner image")
        target = BUILD_DIR / "Resources" / "banner.png"
        copy_and_create_parents(banner, target)
        echo(f"Created {target}")

    echo("Creating distribution file")
    target = BUILD_DIR / "Distribution"
    template = get_template("Distribution")
    render_template(template, data, target)
    pathlib.Path(target).chmod(0o755)
    echo(f"Created {target}")

    # Build the macOS installer package
    echo("Building the macOS installer package")
    build_package(app, version, BUILD_DIR)

    # Build the macOS installer product
    echo("Building the macOS installer product")
    build_product(app, version, BUILD_DIR)


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


def load_from_toml(path: str | os.PathLike) -> dict[str, str]:
    """Load the [tool.applecrate] from a TOML file."""

    data = toml.load(path)
    return data.get("tool", {}).get("applecrate", {})

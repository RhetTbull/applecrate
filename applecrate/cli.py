"""CLI for applecrate to build macOS installer packages."""

from __future__ import annotations

import copy
import os
import pathlib
import shutil
import subprocess
from typing import Any

import click
import markdown2
import toml
from click import echo
from jinja2 import Environment, PackageLoader, Template, select_autoescape

# extra features to support for Markdown to HTML conversion with markdown2
MARKDOWN_EXTRAS = ["fenced-code-blocks", "footnotes", "tables"]
BUILD_DIR = pathlib.Path("build/darwin")


@click.group()
def cli():
    """applecrate: A Python package for creating macOS installer packages."""
    pass


@cli.command()
def init():
    """Create a new applecrate project."""
    echo("Creating a new applecrate project.")


@cli.command()
def check():
    """Check the current environment for applecrate."""
    echo("Checking the current environment for applecrate.")


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
    type=click.Path(exists=True),
    help="Path to welcome markdown or HTML file",
)
@click.option(
    "--conclusion",
    "-c",
    type=click.Path(exists=True),
    help="Path to conclusion markdown or HTML file",
)
@click.option(
    "--uninstall",
    "-u",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to uninstall script; " "if not provided, an uninstall script will be created for you." "See also '--no-uninstall'",
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
    "--post-install",
    "-p",
    type=click.Path(dir_okay=False, exists=True),
    help="Path to post-install script; " "if not provided, a post-install script will be created for you.",
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
    license = kwargs["license"]
    banner = kwargs["banner"]
    post_install = kwargs["post_install"]

    # template data
    data = {
        "app": app,
        "version": version,
        "uninstall": not no_uninstall,
        "url": url,
        "install": install,
        "banner": banner,
    }

    echo(f"Building installer package for {app} version {version}.")

    echo("Cleaning build directory")
    clean_build_dir(BUILD_DIR)
    echo("Creating build directories")
    create_build_dirs(BUILD_DIR)

    # Render the welcome and conclusion templates
    echo("Creating welcome.html")
    create_html_file(welcome, BUILD_DIR / "Resources" / "welcome.html", data, "welcome.md")
    echo("Creating conclusion.html")
    create_html_file(conclusion, BUILD_DIR / "Resources" / "conclusion.html", data, "conclusion.md")

    echo("Copying license file")
    copy_and_create_parents(license, BUILD_DIR / "Resources" / "LICENSE.txt")

    echo("Copying install files")
    for src, dst in install:
        stage_install_files(src, dst, BUILD_DIR)

    # Render the uninstall script
    if not no_uninstall:
        echo("Creating uninstall script")
        target = BUILD_DIR / "darwinpkg" / "Library" / "Application Support" / app / version / "uninstall.sh"
        if uninstall:
            copy_and_create_parents(uninstall, target)
        else:
            template = get_template("uninstall.sh")
            render_template(template, data, target)
        pathlib.Path(target).chmod(0o755)
        echo(f"Created {target}")

    echo("Creating post-install script")
    target = BUILD_DIR / "scripts" / "postinstall"
    if post_install:
        copy_and_create_parents(post_install, target)
    else:
        template = get_template("postinstall")
        render_template(template, data, target)
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
    return rendered


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

    if banner := kwargs.get("banner"):
        banner = pathlib.Path(banner)
        if banner.suffix.lower() != ".png":
            raise ValueError("Banner image must be a PNG file")
        kwargs["banner"] = banner


def load_from_toml(path: str | os.PathLike) -> dict[str, str]:
    """Load the [tool.applecrate] from a TOML file."""

    data = toml.load(path)
    return data.get("tool", {}).get("applecrate", {})


def copy_and_create_parents(src: pathlib.Path, dst: pathlib.Path):
    """Copy a file to a destination and create any necessary parent directories."""
    echo(f"Copying {src} to {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)


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


def load_template_from_file(path: pathlib.Path) -> Template:
    """Load a Jinja2 template from a file."""
    with open(path) as file:
        return Template(file.read())


def get_template(name: str) -> Template:
    """Load a Jinja2 template from the package."""

    env = Environment(loader=PackageLoader("applecrate", "templates"), autoescape=select_autoescape())
    return env.get_template(name)


def render_markdown_template(template: Template, data: dict[str, str], output: pathlib.Path):
    """Render and save a Jinja2 template to a file, converting markdown to HTML."""
    md = template.render(**data)
    html = markdown2.markdown(md, extras=MARKDOWN_EXTRAS)
    head = (
        '<head> <meta charset="utf-8" /> <style> body { font-family: Helvetica, sans-serif; font-size: 14px; } </style> </head>'
    )
    html = f"<!DOCTYPE html>\n<html>\n{head}\n<body>\n{html}\n</body>\n</html>"
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as file:
        file.write(html)


def render_template(template: Template, data: dict[str, str], output: pathlib.Path):
    """Render and save a Jinja2 template to a file."""
    rendered = template.render(**data)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as file:
        file.write(rendered)


def create_html_file(
    input_path: pathlib.Path | None,
    output_path: pathlib.Path,
    data: dict[str, str],
    default_template: str,
):
    """Create an HTML file from a markdown or HTML file and render with Jinja2."""

    if input_path:
        template = load_template_from_file(input_path)
    else:
        template = get_template(default_template)

    if not input_path or input_path.suffix.lower() in [".md", ".markdown"]:
        # passed a markdown file or no file at all
        render_markdown_template(template, data, output_path)
    else:
        render_template(template, data, output_path)

    echo(f"Created {output_path}")


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


def check_dependencies():
    """Check for dependencies."""
    echo("Checking for dependencies.")
    if not shutil.which("pkgbuild"):
        raise click.ClickException("pkgbuild is not installed")
    if not shutil.which("productbuild"):
        raise click.ClickException("productbuild is not installed")


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

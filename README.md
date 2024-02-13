# AppleCrate

Package your command line tools into a native macOS installer.

AppleCrate is a tool for creating native macOS installers for your command line tools. It's useful for creating installers for command line tools written in any language. Tools written in interpreted languages like Python will need to be first processed with a tool like [pyinstaller](https://www.pyinstaller.org/) to create a standalone executable.

## Installation

See the [latest release](https://github.com/RhetTbull/applecrate/releases/latest) for the AppleCrate installer package for your platform. This installer includes a signed binary for the `applecrate` command line tool built with [PyApp](https://ofek.dev/pyapp/latest/) and packaged with AppleCrate itself into a signed macOS installer package.

Note: I've not yet figured out how to create a universal binary with PyApp so you'll need to download the correct installer package for your platform, e.g. `applecrate-0.1.7-x86_64-installer.pkg` for Intel Macs and `applecrate-0.1.7-arm64-installer.pkg` for Apple Silicon Macs.

The installer package will add the `applecrate` command line tool to `/usr/local/bin`. You can upgrade to a new version of AppleCrate by running `applecrate self update` (this only works if you installed AppleCrate with the installer package).

Alternatively, you can install AppleCrate with `pip` or `pipx`:

AppleCrate requires Python 3.9 or later.

```bash
pip install applecrate
```

or

```bash
pipx install applecrate
```

## Simple Example

```bash
applecrate build \
--app mytool \
--version 1.0.0 \
--license LICENSE \
--install dist/mytool "/usr/local/bin/{{ app }}-{{ version }}" \
--link "/usr/local/bin/{{ app }}-{{ version }}" "/usr/local/bin/mytool"
```

This will create a native macOS installer for the tool `dist/mytool` which will install it to `/usr/local/bin/mytool-1.0.0`. The installer will create a symlink to the tool at `/usr/local/bin/mytool` and will also create an uninstaller to remove the tool.

You can also use applecrate from your own Python code to create installers programmatically:

```python
"""Create a macOS installer package programmatically."""

from applecrate import build_installer

if __name__ == "__main__":
    build_installer(
        app="MyApp",
        version="1.0.0",
        license="LICENSE",
        install=[("dist/myapp", "/usr/local/bin/myapp")],
        output="build/{{ app }}-{{ version }}.pkg",
        verbose=print,
    )
```

![Screenshot](https://github.com/RhetTbull/applecrate/blob/main/screenshot.png?raw=true)

## How It Works

AppleCrate is a Python application that uses the `pkgbuild` and `productbuild` command line tools to create a macOS installer package. AppleCrate does not do anything that you couldn't do yourself with these tools, but it automates the process and provide a simple command line interface. Creating a macOS installer package is a multi-step process that requires the generation of multiple files such as HTML files for the welcome screen, pre and post install scripts, Distribution XML file, etc. AppleCrate takes care of all of this for you but also allows you to customize the installer by providing your own files for these steps.

AppleCrate uses [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/) templates to generate the files required for the installer. This allows you to use template variables in your files or command line parameters to customize the installer. For example, you can use `{{ app }}` and `{{ version }}` in your files to refer to the app name and version you provide on the command line.

## Usage

<!--[[[cog
from applecrate.cli import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli, ["build", "--help"])
help = result.output.replace("Usage: cli", "Usage: applecrate")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: applecrate build [OPTIONS]

  applecrate: A Python package for creating macOS installer packages.

Options:
  -a, --app TEXT                  App name.
  -v, --version TEXT              App version.
  -I, --identifier TEXT           Unique package identifier. The OS X Installer
                                  recognizes a package as being an upgrade to an
                                  already-installed package only if the package
                                  identifiers match, so it is advisable to set a
                                  meaningful, consistent identifier when you
                                  build the package. If not set, the identifier
                                  will be set to 'org.opensource.{{ app }}'.
  -l, --license FILE              Path to license file. If provided, the
                                  installer will include a click-through license
                                  agreement.
  -w, --welcome FILE              Path to welcome markdown or HTML file
  -c, --conclusion FILE           Path to conclusion markdown or HTML file
  -u, --uninstall FILE            Path to uninstall script; if not provided, an
                                  uninstall script will be created for you. See
                                  also '--no-uninstall'
  -U, --no-uninstall              Do not include an uninstall script in the
                                  package
  -L, --url NAME URL              Links to additional resources to include in
                                  conclusion HTML shown after installation. For
                                  example, the project website or documentation.
  -b, --banner FILE               Path to optional PNG banner image for
                                  installer package.
  -i, --install FILE_OR_DIR DEST  Install FILE_OR_DIR to destination DEST; DEST
                                  must be an absolute path, for example
                                  '/usr/local/bin/app'. DEST may include
                                  template variables {{ app }} and {{ version
                                  }}. For example: `--install dist/app
                                  "/usr/local/bin/{{ app }}-{{ version }}"` will
                                  install the file 'dist/app' to
                                  '/usr/local/bin/app-1.0.0' if --app=app and
                                  --version=1.0.0.
  -k, --link SRC TARGET           Create a symbolic link from SRC to DEST after
                                  installation. SRC and TARGET must be absolute
                                  paths and both may include template variables
                                  {{ app }} and {{ version }}. For example:
                                  `--link "/Library/Application Support/{{ app
                                  }}/{{ version }}/app" "/usr/local/bin/{{ app
                                  }}-{{ version }}"`
  -p, --pre-install FILE          Path to pre-install shell script; if not
                                  provided, a pre-install script will be created
                                  for you.
  -P, --post-install FILE         Path to post-install shell script; if not
                                  provided, a post-install script will be
                                  created for you. If provided, the installer
                                  will run this script after other post-install
                                  actions.
  -m, --chmod MODE PATH           Change the mode of PATH to MODE after
                                  installation. PATH must be an absolute path.
                                  PATH may contain template variables {{ app }}
                                  and {{ version }}. MODE must be an octal
                                  number, for example '755'.
  -s, --sign APPLE_DEVELOPER_CERTIFICATE_ID
                                  Sign the installer package with a developer
                                  ID. If APPLE_DEVELOPER_CERTIFICATE_ID starts
                                  with '$', it will be treated as an environment
                                  variable and the value of the environment
                                  variable will be used as the developer ID.
  -d, --build-dir DIRECTORY       Build directory to use for building the
                                  installer package. Default is
                                  build/applecrate/darwin if not provided.
  -o, --output FILE               Path to save the installer package.
  --help                          Show this message and exit.

```
<!--[[[end]]] -->

## Configuration

The command line tool applecrate can be configured via `pyproject.toml` or `applecrate.toml` in the current working directory or via command line options. The command line arguments will always take precedence over the configuration files. If present, `applecrate.toml` will take precedence over `pyproject.toml`. The configuration file should be in the following format:

`pyproject.toml`:

```toml
[tool.applecrate]
app = "mytool"
version = "1.0.0"
license = "LICENSE"
install = [
    ["dist/mytool", "/usr/local/bin/{{ app }}-{{ version }}"],
]
sign = "$APPLE_DEVELOPER_CERTIFICATE_ID"
```

`applecrate.toml`:

```toml
app = "mytool"
version = "1.0.0"
license = "LICENSE"
install = [
    ["dist/mytool", "/usr/local/bin/{{ app }}-{{ version }}"],
]
sign = "$APPLE_DEVELOPER_CERTIFICATE_ID"
```

Any command line option is a valid key in the configuration file. For example, the `--app` option can be set in the configuration file as `app = "mytool"`. Command line options with a dash (`-`) should be converted to underscores (`_`) in the configuration file. For example, the `--pre-install` option should be set in the configuration file as `pre_install = "scripts/preinstall.sh"`.

If the value of `sign` begins with a `$`, as in the example above, it will be treated as an environment variable and the value of the environment variable will be used as the certificate ID.

## Template Variables

Destination paths, the package identifier, the welcome and conclusion HTML files, and the pre and post install scripts can include template variables. The following template variables are available:

- `app`: The name of the app.
- `version`: The version of the app.
- `identifier`: The package identifier.
- `uninstall`: The path to the uninstall shell script.
- `url`: A list of URLs to include in the installer package.
- `install`: A list of tuples of source and destination paths to install.
- `banner`: The path to the banner image.
- `link`: A list of tuples of source and target paths to create symlinks post-installation.
- `post_install`: The path to the post-install shell script.
- `pre_install`: The path to the pre-install shell script.
- `chmod`: A list of tuples of mode and path to change the mode of files post-installation.
- `build_dir`: The build directory.
- `output`: The path to the installer package.
- `machine`: The machine architecture, for example `x86_64` or `arm64`.

For example, the default post-install script includes the following to create a symlink:

```bash
{% if link %}
# Create links if needed
{% for source, target in link %}
ln -s "{{ source }}" "{{ target }}"
{% endfor %}
{% endif %}
```

The Jinja2 template engine will replace `{{ source }}` and `{{ target }}` with the source and target paths provided on the command line and remove the `if` and `for` blocks.

See the [Jinja2 template documentation](https://jinja.palletsprojects.com/en/3.0.x/templates/) for more information on how to use template variables.

The package identifier and path arguments such as the build path and the output file path may also be templates but they will only have access to the `app`, `version`, and `machine` variables. Your scripts and welcome/conclusion files will have access to all of the variables.

## Utilities

AppleCrate includes a few utilities for working with installer packages:

```python
from applecrate.pkgutil import pkg_info, pkg_files, extract_pkg
```

- `pkg_info` returns a dictionary of information about the package:
- `pkg_files` returns a list of files in the package.
- `extract_pkg` extracts the package to a directory.

```pycon
>>> import os
>>> from applecrate.pkgutil import pkg_info, pkg_files, extract_pkg
>>> pkg_info("dist/applecrate-0.1.6-x86_64-installer.pkg")
{'overwrite-permissions': 'true', 'relocatable': 'false', 'identifier': 'org.rhettbull.applecrate', 'postinstall-action': 'none', 'version': '0.1.6', 'format-version': '2', 'generator-version': 'InstallCmds-830.2 (22G90)', 'auth': 'root'}
>>> pkg_files("dist/applecrate-0.1.6-x86_64-installer.pkg")
['Distribution', 'Resources/conclusion.html', 'Resources/welcome.html', 'applecrate.pkg/postinstall', 'applecrate.pkg/Bom', 'applecrate.pkg/custom_preinstall', 'applecrate.pkg/Payload', 'applecrate.pkg/Scripts', 'applecrate.pkg/preinstall', 'applecrate.pkg/PackageInfo', 'applecrate.pkg/usr/local/bin/applecrate', 'applecrate.pkg/Library/Application Support/applecrate/0.1.6/uninstall.sh']
>>> os.mkdir("temp")
>>> extract_pkg("dist/applecrate-0.1.6-x86_64-installer.pkg", "temp")
>>>
```

## To Do

- [X] Add support for signing the installer with a developer certificate
- [X] Add python API to create installers programmatically
- [X] Tests
- [ ] Add `applecrate check` command to check the configuration without building the installer
- [ ] Documentation (set up mkdocs)
- [ ] Add support for notarizing the installer

## Credits

Heavily inspired by [macOS Installer Builder](https://github.com/KosalaHerath/macos-installer-builder) by [Kosala Herath](https://github.com/KosalaHerath). AppleCrate is a complete rewrite in Python but borrows many ideas from macOS Installer Builder and is thus licensed under the same Apache License, Version 2.0.

## License

Copyright Rhet Turnbull, 2024. Licensed under the Apache License, Version 2.0 (the "License"); you may not use this project except in compliance with the License. You may obtain a copy of the License [here](https://github.com/RhetTbull/applecrate/blob/main/LICENSE).

## Contributing

Contributions of all kinds are welcome! Please see [CONTRIBUTING.md](https://github.com/RhetTbull/applecrate/blob/main/CONTRIBUTING.md) for more information.

## See Also

[macOS-Pkg-Builder](https://github.com/ripeda/macOS-Pkg-Builder), another Python package for creating macOS installer packages. macOS-Pkg-Builder provides a programmatic interface for creating installer packages and is more flexible than AppleCrate. AppleCrate is designed to be simpler and easier to use for common use cases. I wasn't aware of macOS-Pkg-Builder when I started AppleCrate, but I might have used it to implement AppleCrate had I known about it.

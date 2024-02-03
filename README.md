# AppleCrate

Package your command line tools into a native macOS installer.

AppleCrate is a tool for creating native macOS installers for your command line tools. It's useful for creating installers for command line tools written in any language. Tools written in interpreted languages like Python will need to be first processed with a tool like [pyinstaller](https://www.pyinstaller.org/) to create a standalone executable.

## Installation

```bash
pip install applecrate
```

## Simple Example

```bash
applecrate build --app mytool --version 1.0.0 --license LICENSE --install dist/mytool "/usr/local/bin/{{ app }}-{{ version }}" --link /usr/local/bin/mytool "/usr/local/bin/{{ app }}-{{ version }}"
```

This will create a native macOS installer for the tool `dist/mytool` and install it to `/usr/local/bin/mytool-1.0.0`. It will create a symlink to the tool at `/usr/local/bin/mytool` and will also create an uninstaller to remove the tool.

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
  -a, --app TEXT                  App name
  -v, --version TEXT              App version
  -l, --license FILE              Path to license file
  -w, --welcome PATH              Path to welcome markdown or HTML file
  -c, --conclusion PATH           Path to conclusion markdown or HTML file
  -u, --uninstall FILE            Path to uninstall script; if not provided, an
                                  uninstall script will be created for you.See
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
                                  created for you.
  --help                          Show this message and exit.

```
<!--[[[end]]] -->

## To Do

- [ ] Add support for signing the installer with a developer certificate
- [ ] Add support for notarizing the installer
- [ ] Add python API to create installers programmatically
- [ ] Add `applecrate init` command to create a TOML configuration via a wizard
- [ ] Add `applecrate check` command to check the configuration without building the installer
- [ ] Documentation
- [ ] Tests

## Credits

Heavily inspired by [macOS Installer Buidler](https://github.com/KosalaHerath/macos-installer-builder) by [Kosala Herath](https://github.com/KosalaHerath). AppleCrate is a complete rewrite in Python but borrows many ideas from macOS Installer Builder and is thus licensed under the same Apache License, Version 2.0.

## License

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this project except in compliance with the License.

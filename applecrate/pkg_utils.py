"""Utils for working with installer package files."""

import os
import subprocess
import tempfile


def pkg_payload_files(pkg: str | os.PathLike) -> list[str]:
    """Get list of the payload files in a package."""
    return subprocess.run(
        ["pkgutil", "--payload-files", str(pkg)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()


def pkg_files(pkg: str | os.PathLike) -> list[str]:
    """Get list of all the files in a package including non-payload files."""
    with tempfile.TemporaryDirectory() as tempdir:
        extract_pkg(pkg, tempdir)
        return [os.path.relpath(os.path.join(root, file), tempdir) for root, dirs, files in os.walk(tempdir) for file in files]


def extract_pkg(pkg: str | os.PathLike, dest: str | os.PathLike) -> None:
    """Extract the contents of a package to a directory."""
    # this should work with pkgutil --expand-full but it doesn't always
    # xar seems to be more reliable
    # this is a hack but it appears to work
    subprocess.run(
        ["xar", "-xf", str(pkg), "-C", str(dest)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # there will be a .pkg folder that contains the expanded package
    # The contents are: Bom, PackageInfo, Payload, Scripts
    # Payload contains the payload files as a gzipped cpio archive
    # Scripts contains the preinstall, postinstall, and other scripts as a gzipped cpio archive
    # unzip and untar the Payload and Scripts folders

    # find the subfolder ending in .pkg
    pkg_folders = [f for f in os.listdir(str(dest)) if f.endswith(".pkg")]
    if not pkg_folders:
        raise ValueError("No .pkg folder found in the expanded package.")
    pkg_folder = pkg_folders[0]
    subprocess.run(
        [
            "tar",
            "-xzvf",
            f"{str(dest)}/{pkg_folder}/Payload",
            "-C",
            f"{str(dest)}/{pkg_folder}",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        [
            "tar",
            "-xzvf",
            f"{str(dest)}/{pkg_folder}/Scripts",
            "-C",
            f"{str(dest)}/{pkg_folder}",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

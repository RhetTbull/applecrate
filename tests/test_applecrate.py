"""Test applecrate basic functionality."""

import os

import pytest

from applecrate import build_installer
from applecrate.build import BUILD_DIR
from applecrate.pkg_utils import extract_pkg, pkg_files

from .conftest import write_files


def test_build_installer_basic(tmp_path, capsys):
    """Test the build_installer function with output."""
    os.chdir(tmp_path)
    build_installer(
        app="TestApp",
        version="1.0.0",
        verbose=print,
    )
    assert (tmp_path / "build" / "TestApp-1.0.0.pkg").exists()
    captured = capsys.readouterr()
    assert str(BUILD_DIR) in captured.out


def test_build_installer_output(tmp_path):
    """Test the build_installer function with output."""
    os.chdir(tmp_path)
    build_installer(
        app="TestApp",
        version="1.0.0",
        output=tmp_path / "{{ app }}-{{ version }}-Installer.pkg",
    )
    assert (tmp_path / "TestApp-1.0.0-Installer.pkg").exists()


def test_build_installer_build_dir(tmp_path, capsys):
    """Test the build_installer function with build_dir."""
    os.chdir(tmp_path)
    build_installer(
        app="TestApp",
        version="1.0.0",
        build_dir=tmp_path / "build_test",
        output=tmp_path / "test.pkg",
        verbose=print,
    )
    assert (tmp_path / "test.pkg").exists()
    captured = capsys.readouterr()
    assert str(tmp_path / "build_test" / "applecrate") in captured.out


def test_build_installer_files_basic(tmp_path):
    """Test that files are created and have the correct content."""
    os.chdir(tmp_path)
    write_files(
        {
            "LICENSE": "MIT License",
            "uninstall.sh": "#!/bin/bash\necho 'Uninstalling...'",
            "preinstall.sh": "#!/bin/bash\necho 'Preinstalling...'",
            "postinstall.sh": "#!/bin/bash\necho 'Postinstalling...'",
        }
    )
    build_installer(
        app="TestApp",
        version="1.0.0",
        license="LICENSE",
        uninstall="uninstall.sh",
        pre_install="preinstall.sh",
        post_install="postinstall.sh",
        output=tmp_path / "test.pkg",
    )
    assert (tmp_path / "test.pkg").exists()
    package_files = pkg_files(tmp_path / "test.pkg")
    assert "TestApp.pkg/preinstall" in package_files
    assert "TestApp.pkg/postinstall" in package_files
    assert "TestApp.pkg/custom_preinstall" in package_files
    assert "TestApp.pkg/custom_postinstall" in package_files
    assert (
        "TestApp.pkg/Library/Application Support/TestApp/1.0.0/uninstall.sh"
        in package_files
    )
    assert "Resources/welcome.html" in package_files
    assert "Resources/conclusion.html" in package_files
    assert "Resources/LICENSE.txt" in package_files
    assert "Distribution" in package_files

    contents = tmp_path / "contents"
    contents.mkdir()
    extract_pkg(tmp_path / "test.pkg", contents)
    assert (
        contents / "TestApp.pkg" / "custom_preinstall"
    ).read_text() == "#!/bin/bash\necho 'Preinstalling...'"
    assert (
        contents / "TestApp.pkg" / "custom_postinstall"
    ).read_text() == "#!/bin/bash\necho 'Postinstalling...'"
    assert (contents / "Resources/LICENSE.txt").read_text() == "MIT License"


def test_build_installer_no_uninstaller(tmp_path):
    """Test build_installer with no_uninstaller = True."""
    os.chdir(tmp_path)
    build_installer(
        app="TestApp",
        version="1.0.0",
        no_uninstall=True,
        output=tmp_path / "test.pkg",
    )
    assert (tmp_path / "test.pkg").exists()
    package_files = pkg_files(tmp_path / "test.pkg")
    assert (
        "TestApp.pkg/Library/Application Support/TestApp/1.0.0/uninstall.sh"
        not in package_files
    )


def test_build_installer_url(tmp_path):
    """Test build_installer with url."""
    os.chdir(tmp_path)
    build_installer(
        app="TestApp",
        version="1.0.0",
        url=[("TestApp", "https://example.com/testapp")],
        output=tmp_path / "test.pkg",
    )
    assert (tmp_path / "test.pkg").exists()
    contents = tmp_path / "contents"
    contents.mkdir()
    extract_pkg(tmp_path / "test.pkg", contents)
    assert (
        "https://example.com/testapp"
        in (tmp_path / "contents" / "Resources" / "conclusion.html").read_text()
    )

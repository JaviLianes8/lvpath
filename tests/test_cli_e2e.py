"""Real end-to-end tests: pip-install the package and drive the real console script.

These build a throwaway virtual environment, install the project into it in
editable mode, and run the installed ``lvpath`` executable as a subprocess. They
assert the real process stdout and exit status, not an in-process import, and
prove the NI golden vector round-trips byte for byte through the shipped CLI.
"""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_HEX = "505448300000000b0000000201430466696c65"


@pytest.fixture(scope="module")
def lvpath_exe(tmp_path_factory: pytest.TempPathFactory) -> Path:
    env_dir = tmp_path_factory.mktemp("venv")
    venv.create(env_dir, with_pip=True)
    scripts = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = scripts / ("python.exe" if sys.platform == "win32" else "python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--quiet", "--editable", str(PROJECT_ROOT)],
        check=True,
        capture_output=True,
        timeout=600,
    )
    exe = scripts / ("lvpath.exe" if sys.platform == "win32" else "lvpath")
    assert exe.is_file(), f"console script was not installed at {exe}"
    return exe


def _run(exe: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=60)


def test_installed_script_reports_its_version(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "lvpath 0.2.0"


def test_installed_script_decodes_the_golden_vector(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "decode", "--platform", "windows", GOLDEN_HEX)
    assert result.returncode == 0
    assert result.stdout.strip() == "C:\\file"


def test_installed_script_encodes_to_the_golden_vector(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "encode", "--platform", "windows", "C:/file")
    assert result.returncode == 0
    assert result.stdout.strip() == GOLDEN_HEX


def test_installed_script_round_trips_byte_exact(lvpath_exe: Path) -> None:
    encoded = _run(lvpath_exe, "encode", "--platform", "windows", "C:/file")
    assert encoded.returncode == 0
    hex_out = encoded.stdout.strip()
    assert hex_out == GOLDEN_HEX
    decoded = _run(lvpath_exe, "decode", "--platform", "windows", hex_out)
    assert decoded.returncode == 0
    reencoded = _run(lvpath_exe, "encode", "--platform", "windows", decoded.stdout.strip())
    assert reencoded.stdout.strip() == GOLDEN_HEX


def test_installed_script_accepts_spaced_hex(lvpath_exe: Path) -> None:
    spaced = "50 54 48 30 00 00 00 0b 00 00 00 02 01 43 04 66 69 6c 65"
    result = _run(lvpath_exe, "decode", "--platform", "windows", spaced)
    assert result.returncode == 0
    assert result.stdout.strip() == "C:\\file"


def test_installed_script_reports_bad_hex_to_stderr(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "decode", "zzzz")
    assert result.returncode == 1
    assert result.stdout.strip() == ""
    assert "lvpath:" in result.stderr


def test_installed_script_refuses_unc_paths(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "encode", "--platform", "windows", r"\\server\share\file")
    assert result.returncode == 1
    assert "UNC" in result.stderr

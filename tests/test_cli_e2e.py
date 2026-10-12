"""Real end-to-end tests: pip-install the package and drive the real console script.

These build a throwaway virtual environment, install the project into it in
editable mode, and run the installed ``lvpath`` executable as a subprocess. They
assert the real process stdout and exit status, not an in-process import, and
prove the NI golden vector round-trips byte for byte through the shipped CLI.
"""

from __future__ import annotations

import shlex
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
    return subprocess.run([str(exe), *args], capture_output=True, encoding="utf-8", timeout=60)


def test_installed_script_reports_its_version(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "lvpath 0.3.1"


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


# Real path values from files shipped with LabVIEW 2026 (see fixtures/labview2026_paths.json).
REAL_PORTABLE = "/C/Program Files (x86)/Arduino"
REAL_WINDOWS = "C:\\Program Files (x86)\\Arduino"


def test_installed_script_converts_a_real_labview_path_to_native(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "to-native", "--platform", "windows", REAL_PORTABLE)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == REAL_WINDOWS


def test_installed_script_converts_a_native_path_to_labview(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "to-labview", "--platform", "windows", REAL_WINDOWS)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == REAL_PORTABLE


def test_installed_script_round_trips_unc_and_relative(lvpath_exe: Path) -> None:
    for portable in ("//server/share/dir", "../builds/NI_AB_PROJECTNAME/Main Application"):
        native = _run(lvpath_exe, "to-native", "--platform", "windows", portable)
        assert native.returncode == 0, native.stderr
        back = _run(lvpath_exe, "to-labview", "--platform", "windows", native.stdout.strip())
        assert back.returncode == 0, back.stderr
        assert back.stdout.strip() == portable


def test_installed_script_reads_posix_values_unchanged(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "to-native", "--platform", "posix", "/home/lvuser/natinst/bin")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "/home/lvuser/natinst/bin"


def test_installed_script_refuses_not_a_path(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "to-native", "--platform", "windows", "")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "not-a-path" in result.stderr


def test_installed_script_refuses_posix_absolute_on_windows(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "to-native", "--platform", "windows", "/home/lvuser")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "no Windows equivalent" in result.stderr


def test_installed_script_help_lists_runnable_examples(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "--help")
    assert result.returncode == 0
    for command in ("to-native", "to-labview", "decode", "encode"):
        assert f"lvpath {command} --platform" in result.stdout
    lines = [line.strip() for line in result.stdout.splitlines()]
    for index, line in enumerate(lines):
        if not line.startswith("lvpath "):
            continue
        run = _run(lvpath_exe, *shlex.split(line)[1:])
        assert (run.returncode, run.stderr) == (0, ""), line
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if following.startswith("# prints "):
            assert run.stdout == following.removeprefix("# prints ") + "\n", line


@pytest.mark.parametrize(
    ("portable", "native"),
    [("/c/ni-rt/startup", "c:\\ni-rt\\startup"), ("/D", "D:\\"), (" a /b ", " a \\b ")],
)
def test_installed_script_prints_drives_and_spaces_exactly(
    lvpath_exe: Path, portable: str, native: str
) -> None:
    result = _run(lvpath_exe, "to-native", "--platform", "windows", portable)
    assert (result.returncode, result.stdout, result.stderr) == (0, native + "\n", "")
    back = _run(lvpath_exe, "to-labview", "--platform", "windows", native)
    assert (back.returncode, back.stdout, back.stderr) == (0, portable + "\n", "")


def test_installed_script_writes_not_a_path_as_an_empty_line(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "to-labview", "--platform", "windows", "")
    assert (result.returncode, result.stdout, result.stderr) == (0, "\n", "")


def test_installed_script_to_labview_refuses_a_drive_relative_path(lvpath_exe: Path) -> None:
    result = _run(lvpath_exe, "to-labview", "--platform", "windows", "C:file")
    assert (result.returncode, result.stdout) == (1, "")
    assert "drive-relative" in result.stderr


def test_installed_script_prints_non_ascii_paths_through_a_pipe(lvpath_exe: Path) -> None:
    name = "Data \u0101\u4e2d"
    result = _run(lvpath_exe, "to-native", "--platform", "windows", f"/C/{name}")
    assert (result.returncode, result.stdout, result.stderr) == (0, f"C:\\{name}\n", "")
    back = _run(lvpath_exe, "to-labview", "--platform", "windows", f"C:\\{name}")
    assert (back.returncode, back.stdout, back.stderr) == (0, f"/C/{name}\n", "")

"""More end-to-end runs of the installed package: ``python -m``, exit statuses, closed pipes."""

from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import ENV

import lvpath


def _run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, encoding="utf-8", timeout=60, env=ENV)


def test_python_dash_m_runs_the_same_command(installed: tuple[Path, Path]) -> None:
    python = str(installed[0])
    result = _run(python, "-m", "lvpath", "to-labview", "--platform", "windows", "C:/x")
    assert (result.returncode, result.stdout, result.stderr) == (0, "/C/x\n", "")
    version = _run(python, "-m", "lvpath", "--version")
    assert version.stdout.strip() == f"lvpath {lvpath.__version__}"


def test_usage_mistakes_exit_two_with_a_short_message(installed: tuple[Path, Path]) -> None:
    script = str(installed[1])
    for args in ([], ["decode", "--platform", "mac" * 5000, "00"], ["nope" * 5000]):
        result = _run(script, *args)
        assert result.returncode == 2, args
        assert result.stdout == ""
        assert all(len(line) <= 200 for line in result.stderr.splitlines()), args


def test_a_refused_value_exits_one_with_one_bounded_line(installed: tuple[Path, Path]) -> None:
    result = _run(str(installed[1]), "to-native", "--platform", "windows", "/home" * 5_000)
    assert (result.returncode, result.stdout) == (1, "")
    assert len(result.stderr.splitlines()) == 1
    assert len(result.stderr) < 200


def test_an_up_level_link_round_trips_through_the_installed_command(
    installed: tuple[Path, Path],
) -> None:
    script = str(installed[1])
    encoded = _run(script, "encode", "--platform", "posix", "../../NI_MDF.lvlib")
    assert encoded.stdout.strip() == "50544830000000130001000300000c4e495f4d44462e6c766c6962"
    decoded = _run(script, "decode", "--platform", "windows", encoded.stdout.strip())
    assert (decoded.returncode, decoded.stdout) == (0, "..\\..\\NI_MDF.lvlib\n")


def test_a_closed_output_pipe_exits_one_quietly(installed: tuple[Path, Path]) -> None:
    command = [str(installed[1]), "to-labview", "--platform", "posix", "a" * 30_000]
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV
    ) as process:
        assert process.stdout is not None and process.stderr is not None
        process.stdout.close()
        error = process.stderr.read()
        status = process.wait(timeout=60)
    assert (status, error) == (1, b"")

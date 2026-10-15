"""A throwaway virtual environment with the built wheel installed, for the end-to-end tests.

``LVPATH_WHEEL`` names a wheel to install; otherwise one is built from this source tree. The
venv shares nothing with the test runner, so the tests drive the real installed package.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_LEAKY = ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONSTARTUP")
ENV = {key: value for key, value in os.environ.items() if key.upper() not in _LEAKY}


def _wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    given = os.environ.get("LVPATH_WHEEL")
    if given:
        return Path(given)
    if not (ROOT / "src" / "lvpath" / "__init__.py").is_file():
        pytest.skip("no source tree to build from; set LVPATH_WHEEL to a built wheel")
    wheels = tmp_path_factory.mktemp("wheels")
    build = [sys.executable, "-m", "pip", "wheel", "--quiet", "--no-deps"]
    if importlib.util.find_spec("hatchling") is not None:
        build.append("--no-build-isolation")
    subprocess.run([*build, "-w", str(wheels), str(ROOT)], check=True, timeout=600, env=ENV)
    (wheel,) = wheels.glob("lvpath-*.whl")
    return wheel


@pytest.fixture(scope="session")
def installed(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """The venv's Python and its ``lvpath`` console script."""
    wheel = _wheel(tmp_path_factory)
    with zipfile.ZipFile(wheel) as archive:
        assert "lvpath/__init__.py" in archive.namelist(), "the wheel holds no package"
    env_dir = tmp_path_factory.mktemp("venv")
    venv.EnvBuilder(with_pip=True).create(env_dir)
    scripts = env_dir / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    install = [str(python), "-m", "pip", "install", "--quiet", "--no-index", "--no-deps"]
    subprocess.run([*install, str(wheel)], check=True, timeout=600, env=ENV)
    where = [str(python), "-c", "import lvpath; print(lvpath.__file__)"]
    location = subprocess.run(
        where, check=True, capture_output=True, text=True, cwd=env_dir, env=ENV
    )
    assert Path(location.stdout.strip()).resolve().is_relative_to(env_dir.resolve())
    found = shutil.which("lvpath", path=str(scripts))
    assert found is not None, "pip did not install the lvpath console script"
    return python, Path(found)

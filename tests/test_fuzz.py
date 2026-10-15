"""Seeded fuzz and property tests: no crash outside the documented errors, no blow-up."""

from __future__ import annotations

import contextlib
import random
import string
import time
from collections.abc import Callable

import pytest

from lvpath import (
    FlatPath,
    FlatPathError,
    NotAPathError,
    PortablePathError,
    from_flat_path,
    from_portable_path,
    parse_flat_path,
    path_kind,
    to_flat_path,
    to_lv_path,
    to_portable_path,
)

_SEED = 20261015
_EXPECTED = (FlatPathError, PortablePathError, NotAPathError)
_ALPHABET = string.ascii_letters + string.digits + "/\\:.<> -_?" + "é中"


def _mutated_flat(rng: random.Random) -> bytes:
    parts = tuple(
        "".join(rng.choice(string.printable[:94]) for _ in range(rng.randrange(6)))
        for _ in range(rng.randrange(5))
    )
    data = bytearray(FlatPath(rng.choice([0, 1, 2, 3]), parts).to_bytes())
    for _ in range(rng.randrange(4)):
        action = rng.randrange(3)
        if action == 0 and data:
            data[rng.randrange(len(data))] = rng.randrange(256)
        elif action == 1 and data:
            del data[rng.randrange(len(data)) :]
        else:
            data.insert(rng.randrange(len(data) + 1), rng.randrange(256))
    return bytes(data)


def test_mutated_flattened_bytes_parse_or_raise_flat_path_error() -> None:
    rng = random.Random(_SEED)
    for _ in range(20_000):
        data = _mutated_flat(rng)
        try:
            flat = parse_flat_path(data)
        except FlatPathError:
            continue
        assert flat.to_bytes() == data
        for platform in ("windows", "posix"):
            try:
                pure = from_flat_path(data, platform=platform)
            except (FlatPathError, NotAPathError):
                continue
            assert to_flat_path(pure, platform=platform) == data


def test_random_text_never_escapes_the_documented_errors() -> None:
    rng = random.Random(_SEED + 1)
    calls: list[Callable[[str, str], object]] = [
        lambda text, platform: from_portable_path(text, platform=platform),
        lambda text, platform: to_portable_path(text, platform=platform),
        lambda text, platform: to_flat_path(text, platform=platform),
        lambda text, platform: path_kind(text, platform=platform),
        lambda text, platform: to_lv_path(text, platform=platform),
    ]
    for _ in range(20_000):
        text = "".join(rng.choice(_ALPHABET) for _ in range(rng.randrange(12)))
        for call in calls:
            try:
                call(text, rng.choice(["windows", "posix"]))
            except _EXPECTED as error:
                assert len(str(error)) < 200


def _normal_portable(rng: random.Random) -> str:
    names = [
        "".join(rng.choice(string.ascii_letters + " ()_-.") for _ in range(rng.randrange(1, 8)))
        for _ in range(rng.randrange(4))
    ]
    names = [n.strip(" .") or "x" for n in names]
    head = rng.choice(["/" + rng.choice(string.ascii_letters), "//srv/share", "", ".."])
    if head == "" and not names:
        names = ["x"]
    return "/".join([head, *names]) if head else "/".join(names)


def test_normal_portable_values_round_trip_exactly_on_windows() -> None:
    rng = random.Random(_SEED + 2)
    for _ in range(5_000):
        value = _normal_portable(rng)
        native = from_portable_path(value, platform="windows")
        assert to_portable_path(native, platform="windows") == value, value


def _linear(call: Callable[[int], object]) -> None:
    def cost(size: int) -> float:
        best = float("inf")
        for _ in range(3):
            start = time.perf_counter()
            call(size)
            best = min(best, time.perf_counter() - start)
        return best

    small, large = cost(20_000), cost(200_000)
    assert large < 40 * small + 0.05


@pytest.mark.parametrize(
    "call",
    [
        lambda n: path_kind("a\\" * n, platform="windows"),
        lambda n: _swallow(lambda: from_portable_path("/C:" + "x" * n, platform="windows")),
        lambda n: _swallow(lambda: to_portable_path("\\\\" + "x" * n, platform="windows")),
        lambda n: _swallow(lambda: parse_flat_path(b"PTH0" + bytes(n))),
        lambda n: from_flat_path(FlatPath(1, ("ab",) * (n // 10)).to_bytes(), platform="posix"),
        lambda n: to_flat_path("a/" * (n // 10), platform="posix"),
    ],
)
def test_hostile_sizes_scale_linearly(call: Callable[[int], object]) -> None:
    _linear(call)


def _swallow(call: Callable[[], object]) -> None:
    with contextlib.suppress(*_EXPECTED):
        call()

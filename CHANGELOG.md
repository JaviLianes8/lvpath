# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-15

The public surface is now stable: the seventeen names of 0.3.1 (three of them exception classes) with the same
parameters and defaults (some annotations widened, listed below), the `lvpath` command and `python -m lvpath`.
The flattened form is checked against NI's published example and against the
349,566 flattened paths LabVIEW 2026 stores in its own installed files.

### Changed

- An empty flattened component now decodes as `..` and `..` encodes as an empty
  component, which is how LabVIEW 2026 stores relative links (21,765 links in its own
  files resolve that way). 0.3.1 dropped the empty components, so
  `('', '', 'NI_MDF.lvlib')` decoded as `NI_MDF.lvlib`, and wrote `..` as two dots.
- `<Not A Path>` in the flattened form is path type 2 with no component, the code
  LabVIEW's `cintools/extcode.h` gives it and the record LabVIEW 2026 stores in
  `resource/labview.rsc`. `to_flat_path("")` and `to_flat_path(None)` now write it (0.3.1
  wrote `""` as an empty relative path, which decodes as `.`, and raised
  `AttributeError` for `None`), and `from_flat_path` raises `NotAPathError` for it (0.3.1:
  `FlatPathError`). `FlatPathType` gains `NOT_A_PATH` (2) and `UNC` (3); a UNC flattened
  path is still refused with `FlatPathError`.
- `from_flat_path` refuses with `FlatPathError` what 0.3.1 misread: a symbolic
  `<vilib>`-style first component of an absolute path, a first Windows component that is
  not one drive letter (0.3.1 produced `usr:\lib`), literal `.` and `..` components, and
  components holding `/` (or `\` or `:` on Windows).
- `to_flat_path` refuses a POSIX path starting with `//` (0.3.1 dropped one slash) and a
  rooted Windows path without a drive such as `\usr\x` (0.3.1 wrote it as a relative path
  whose first component was a backslash).
- One flavor rule for `PurePath` arguments in every function: a `PurePath` keeps its own
  flavor unless `platform` names the other one, and then only a relative path may cross,
  with no backslash or colon inside a component on the way to Windows; anything else
  raises `PortablePathError` (`FlatPathError` in `to_flat_path`). 0.3.1 re-read a
  `PurePath` with the flavor of `platform` (or of the running system) in `to_lv_path`,
  `to_flat_path`, `to_os_path`, `path_kind` and, on POSIX, `from_portable_path`, producing a different path for anchored
  ones, and `from_portable_path` raised `TypeError` for a `PurePath` on Windows. The
  annotations of `to_os_path`, `path_kind` and `from_portable_path` now include
  `PurePath`, and that of `to_flat_path` includes `None`.
- `platform` is checked before anything else in every function: an unknown name raises
  `ValueError` and a value that is not a `str`, `Platform` or `None` raises `TypeError`
  (0.3.1 raised `AttributeError`), even when the path is empty or the bytes are malformed.
  In 0.3.1, `path_kind("", platform="bogus")` returned `NOT_A_PATH`, `to_lv_path` and
  `to_portable_path` returned `""`, `to_os_path` and `from_portable_path` raised
  `NotAPathError` and `from_flat_path` raised `FlatPathError` for bad bytes.
- Arguments of the wrong type raise `TypeError` with a short message. 0.3.1 returned
  `'5'` for `to_portable_path(5)` and `"b'x'"` for `to_portable_path(b"x")`, raised
  `AttributeError` for `to_lv_path(5)` and `to_flat_path(5)`, and raised `FlatPathError`
  for `parse_flat_path` given a short `str`.
- `FlatPath` checks its fields when built: a `bool` or non-integer path type and a
  non-`str` component raise `TypeError` (0.3.1 accepted `FlatPath(0, "ab")`); a non-ASCII
  or over-long component raises `FlatPathError` at once (0.3.1 raised it later, in
  `to_bytes`). The path type is stored as a plain `int` (0.3.1 kept an `IntEnum` member as
  given) and the components as a tuple. `build_flat_path` refuses a `str` as its
  components with `TypeError` (0.3.1 split it into one-character components). A pickle
  written by 0.3.1 loads with its fields normalised the same way.
- Non-ASCII flattened bytes raise `FlatPathError` instead of `UnicodeDecodeError`.
  `parse_flat_path`, `FlatPath.from_bytes` and `from_flat_path` read the raw bytes of any
  object with the buffer protocol (`bytes`, `bytearray`, `memoryview`, `array`, `mmap`)
  and are typed for `bytes | bytearray | memoryview`. 0.3.1 read `bytes` and
  `bytearray` only: a `memoryview` or `array` holding a component raised
  `AttributeError`, and a wide `array` was measured in items.
- Error messages quote at most 40 characters of a value and several are reworded; the
  exception types are unchanged except where listed here. The public classes
  (`FlatPath`, `FlatPathType`, `PathKind`, `Platform` and the three exceptions) report
  their module as `lvpath`, so pickles name `lvpath.<class>`; pickles made by 0.3.1 still
  load.
- Command line: a usage mistake still exits 2, now with lines of at most 200 characters;
  a refused value prints one bounded line and exits 1; a closed output pipe exits 1
  quietly; invalid hex no longer echoes the parser's detail; `lvpath encode ''` prints the
  not-a-path bytes and `lvpath decode` of them is refused. A POSIX argument that is not
  valid UTF-8 is written back as its original bytes (0.3.1 stopped with a
  `UnicodeEncodeError` traceback); a lone surrogate UTF-8 cannot write at all (possible
  in Windows arguments) is refused in one line with status 1; a missing standard stream
  no longer raises.
- A `str` subclass is read through its plain text: an overridden `__eq__` or `__len__`
  no longer changes a result or slips past the component limits.

### Added

- `python -m lvpath`.
- `FlatPathType.NOT_A_PATH` and `FlatPathType.UNC`.
- `GUIDE.md` with the rules, the errors table, the ground truth and upgrade notes.
- Docstring examples for every public name, run as doctests.

## [0.3.1]

- The LabVIEW 2026 path fixture no longer carries source lines copied from NI files: each
  row keeps only the path value, its expected renderings, and where it was found (file and
  setting). The sdist is limited to the package, the tests and the docs.

## [0.3.0]

- Added the portable path form LabVIEW writes into configuration and project
  files. `from_portable_path` reads `/C/DIR1/DIR2` as `C:\DIR1\DIR2`,
  `//server/share/dir` as a UNC path and `../a/b` as a relative path;
  `to_portable_path` writes them back, keeping the drive letter case. The empty value is `<Not A Path>`.
- `PortablePathError` reports a value with no faithful counterpart instead of
  rewriting it into another path: a POSIX absolute path read as Windows, a
  drive-relative `C:file`, a rooted Windows path without a drive, a UNC path
  without a share and a `\\?\` device path.
- The `lvpath` command line gains `to-native` and `to-labview`, and its help lists
  runnable examples for every subcommand.
- The test suite carries a verbatim excerpt of path values from files shipped with
  LabVIEW 2026 and checks every value in both directions and through a round trip.
- The README no longer implies that `to_os_path` translates `/C/foo`; it documents
  the portable form, its rules and its one ambiguity.

## [0.2.0]

- Added the binary flattened path form (`Flatten To String` `PTH0`). `FlatPath` is
  a typed, frozen result with `to_bytes` and `from_bytes`; `parse_flat_path` and
  `build_flat_path` are the codec entry points. The NI `C:\File` example round-trips
  byte for byte in both directions.
- `to_flat_path` and `from_flat_path` bridge the flattened form to and from
  `pathlib.PurePath` on a chosen platform flavor.
- `FlatPathType` exposes the two documented path type codes (absolute `0`, relative
  `1`). UNC and not-a-path codes are undocumented, so they are not guessed: the
  codec still round-trips their raw bytes, while the PurePath bridge refuses an
  un-interpretable type code with `FlatPathError`.
- Added an `lvpath` command line with `decode` and `encode` subcommands and
  `--version`.

## [0.1.0]

- First release.
- `to_os_path` parses a LabVIEW path string into a `PurePath` of the Windows or
  POSIX flavor; `to_lv_path` serializes an OS path back into a LabVIEW string.
- `path_kind` and `PathKind` detect absolute, relative and not-a-path values;
  the empty string is the not-a-path value on every platform.
- `NotAPathError` is raised when the not-a-path value is converted to an OS path.
- Covers the textual `Path To String` / `String To Path` conventions: Windows
  drive and UNC anchors, POSIX roots, lenient forward slashes, and clean
  cross-platform conversion of relative path objects. Classic Mac OS colon paths
  and the binary flatten path type are out of scope.

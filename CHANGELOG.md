# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-15

The public surface is now stable: the seventeen names of 0.3.1 with the same signatures
and defaults, the three exception classes, the `lvpath` command and `python -m lvpath`.
The flattened form is checked against NI's published example and against the
349,566 flattened paths LabVIEW 2026 stores in its own installed files.

### Changed

- An empty flattened component now decodes as `..` and `..` encodes as an empty
  component, which is how LabVIEW 2026 stores relative links (21,765 links in its own
  files resolve that way). 0.3.1 dropped the empty components, so
  `('', '', 'NI_MDF.lvlib')` decoded as `NI_MDF.lvlib`.
- `from_flat_path` refuses with `FlatPathError` what it used to misread: a symbolic
  `<vilib>`-style first component, a first Windows component that is not a drive letter
  (0.3.1 produced `usr:\lib`), the absolute path with no component on Windows, literal
  `.` and `..` components, and components holding `/` (or `\` or `:` on Windows).
- `to_flat_path` refuses a POSIX path starting with `//` (0.3.1 dropped one slash).
- A `PurePath` passed to `to_lv_path` or `to_flat_path` with `platform=None` keeps its own
  flavor, as `to_portable_path` already did; an anchored path is no longer carried to the
  other flavor, and a component with a colon may not cross to Windows (raises
  `PortablePathError` or `FlatPathError`).
- `FlatPath` checks its fields when built: a non-integer or `bool` path type and a non-`str`
  component raise `TypeError`, a non-ASCII, over-long or 65,536th component
  `FlatPathError`. Components given as any iterable are stored as a tuple.
- Non-ASCII flattened bytes raise `FlatPathError` instead of `UnicodeDecodeError`.
  `parse_flat_path`, `FlatPath.from_bytes` and `from_flat_path` accept `bytearray` and
  `memoryview` and raise `TypeError` for anything else.
- A `platform` that is not a `str`, `Platform` or `None` raises `TypeError` instead of
  `AttributeError`. Non-`str` text arguments raise `TypeError` with a short message.
- Error messages quote at most 40 characters of a value; the exception classes report
  their module as `lvpath`.
- Command line: usage mistakes print the usage and one bounded line and exit 2, refused
  values one bounded line and exit 1, a closed output pipe exits 1 quietly; invalid hex no
  longer echoes the parser's detail.

### Added

- `python -m lvpath`.
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

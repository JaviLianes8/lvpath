# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

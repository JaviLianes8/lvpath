# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

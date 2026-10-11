# lvpath

Convert between LabVIEW path strings and native OS paths, with absolute, relative and not-a-path detection.

## Install

```
pip install lvpath
```

## Usage

```python
from lvpath import to_os_path, to_lv_path, path_kind, PathKind, NotAPathError

# Parse a LabVIEW path string into a PurePath of the chosen platform flavor.
to_os_path("C:\\Users\\test\\data.txt", platform="windows")
# PureWindowsPath('C:/Users/test/data.txt')

to_os_path("/usr/local/bin", platform="posix")
# PurePosixPath('/usr/local/bin')

# Serialize an OS path back into a LabVIEW path string.
to_lv_path("logs/run.txt", platform="windows")
# 'logs\\run.txt'

# A relative path object crosses platforms cleanly.
win = to_os_path("reports\\q1\\data.txt", platform="windows")
to_lv_path(win, platform="posix")
# 'reports/q1/data.txt'

# Detect the kind. The empty string is LabVIEW's <Not A Path> on every platform.
path_kind("", platform="posix")            # PathKind.NOT_A_PATH
path_kind("sub\\file", platform="windows")  # PathKind.RELATIVE
path_kind("C:\\x", platform="windows")      # PathKind.ABSOLUTE

# Not-a-path has no OS equivalent, so to_os_path refuses it.
try:
    to_os_path("", platform="posix")
except NotAPathError:
    ...

# None (or "") serializes back to the not-a-path value.
to_lv_path(None, platform="windows")  # ''
```

`platform` accepts `"windows"`, `"posix"`, a `Platform` member, or `None` to use
the convention of the operating system running the code.

## Covered conventions

LabVIEW's `Path To String` and `String To Path` render and parse a path in the
standard textual form of a host platform. This library models that textual form:

- **Separators:** `\` on Windows, `/` on POSIX. Forward slashes are also accepted
  when parsing a Windows path, matching LabVIEW's lenient reader.
- **Absolute, Windows:** drive-letter paths (`C:\dir\file`) and UNC paths
  (`\\server\share\dir`).
- **Absolute, POSIX:** a leading `/` (modern LabVIEW on macOS and Linux).
- **Relative:** any other non-empty string, including up-level (`..\up`) and
  drive-relative (`C:file`) forms.
- **Not-a-path:** the empty string, LabVIEW's `<Not A Path>` value, on every
  platform. `None` serializes back to it.

### What it does not do

- It does not touch the filesystem, resolve symbolic links, or normalise `.`/`..`
  beyond what `pathlib` does.
- It does not handle classic Mac OS colon-separated paths (pre-OS X). Modern
  LabVIEW on macOS uses POSIX `/`.
- It covers the textual path form, not the binary `Flatten To String` path type,
  which is a separate serialization.

## Why

LabVIEW serializes a path in the standard textual form of its host platform, and
that form differs from `os.path`: platform-dependent separators, drive and UNC
anchors, and the empty string standing for `<Not A Path>`. LabVIEW does not
translate separators when a path crosses platforms (for example a Windows string
read on macOS keeps its backslashes), so round-tripping LabVIEW path data in
Python needs explicit, platform-aware handling. No PyPI package does this: the
existing options are LabVIEW's own built-in functions and the generic `pathlib`,
which has no notion of a foreign-platform LabVIEW string or of not-a-path. This
library fills that gap with a small, typed, zero-dependency surface.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

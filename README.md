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
path_kind("", platform="posix")  # PathKind.NOT_A_PATH
path_kind("sub\\file", platform="windows")  # PathKind.RELATIVE
path_kind("C:\\x", platform="windows")  # PathKind.ABSOLUTE

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

## Flattened form

`Flatten To String` renders a LabVIEW Path as a small big-endian binary
container: the ASCII signature `PTH0`, a `u32` total length, a `u16` path type, a
`u16` component count and then one length-prefixed (Pascal) string per component.
NI documents the absolute path `C:\File` flattening to the bytes
`50 54 48 30  00 00 00 0B  00 00  00 02  01 43  04 66 69 6C 65`.

```python
from lvpath import FlatPath, parse_flat_path, from_flat_path, to_flat_path

golden = bytes.fromhex("505448300000000b0000000201430466696c65")

# Parse the flattened bytes into a typed result.
parse_flat_path(golden)
# FlatPath(path_type=0, components=('C', 'file'))

# Round-trips byte for byte.
parse_flat_path(golden).to_bytes() == golden  # True

# Bridge to and from pathlib on a chosen platform flavor.
from_flat_path(golden, platform="windows")  # PureWindowsPath('C:/file')
to_flat_path("C:/file", platform="windows")  # the golden bytes
to_flat_path("/usr/local/bin", platform="posix")  # a POSIX absolute flattened path
```

Only the two documented path type codes are interpreted: `0` absolute and `1`
relative, exposed as `FlatPathType`. UNC and empty / not-a-path forms carry type
codes the public NI documentation does not state, so they are not guessed: the
low-level codec still round-trips their raw bytes faithfully through `FlatPath`,
while `to_flat_path` and `from_flat_path` refuse an un-interpretable type code
with a clear `FlatPathError` instead of inventing a meaning.

## Command line

Installing the package provides an `lvpath` command for the flattened form.

```
# Decode the NI C:\File flattened example into a path.
lvpath decode --platform windows 505448300000000b0000000201430466696c65
# C:\file

# Encode a path into its flattened hex form.
lvpath encode --platform windows "C:\file"
# 505448300000000b0000000201430466696c65

lvpath --version
```

`lvpath decode` accepts hex with or without spaces. Errors are written to standard
error and the command exits with status 1. Run `lvpath --help` for the full usage.

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
- The flattened codec interprets only the documented absolute and relative path
  type codes. It does not guess the undocumented UNC or not-a-path type codes, and
  it does not touch the textual-form behaviour above.

## Why

LabVIEW serializes a path in the standard textual form of its host platform, and
LabVIEW does not translate separators when a path crosses platforms (for example a
Windows string read on macOS keeps its backslashes), so round-tripping LabVIEW path
data in Python needs explicit, platform-aware handling.

The standard library already does most of this. `pathlib`'s `PureWindowsPath` and
`PurePosixPath` are built to manipulate foreign-platform paths with no I/O, so they
cover the bulk of the separator and anchor handling on their own, and this library is
a thin wrapper over them rather than a reimplementation. What they do not know is the
genuinely LabVIEW-specific residue: the leading-slash drive form (`/C/foo` to
`C:\foo`), the empty string standing for `<Not A Path>`, and LabVIEW's exact
serialization rules. No PyPI package targets those conventions. `lvpath` adds exactly
that layer on top of `pathlib`, with a small, typed, zero-dependency surface.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

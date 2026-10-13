# lvpath

Convert between LabVIEW path strings and native OS paths: the host text form, the
portable form LabVIEW writes into config and project files (`/C/DIR1/DIR2`), and the
flattened `PTH0` binary form, with absolute, relative and not-a-path detection.

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

## Portable form (config and project files)

When LabVIEW writes a path value into a configuration (`.ini`) file or a project
(`.lvproj`) file, it does not use the native Windows text. It uses a
platform-independent form: the drive letter becomes a leading component, every
separator is a forward slash, a UNC share keeps a leading double slash and the empty
string is `<Not A Path>`. `C:\DIR1\DIR2` is stored as `/C/DIR1/DIR2`.

```python
from lvpath import from_portable_path, to_portable_path, PortablePathError

# Read a stored value into a native path.
from_portable_path("/C/Program Files (x86)/Arduino", platform="windows")
# PureWindowsPath('C:/Program Files (x86)/Arduino')
from_portable_path("//server/share/dir", platform="windows")
# PureWindowsPath('//server/share/dir')
from_portable_path("../builds/Main Application", platform="windows")
# PureWindowsPath('../builds/Main Application')
from_portable_path("/home/lvuser/natinst/bin", platform="posix")
# PurePosixPath('/home/lvuser/natinst/bin')

# Write a native path back in the stored form.
to_portable_path("C:\\DIR1\\DIR2", platform="windows")  # '/C/DIR1/DIR2'
to_portable_path("D:\\", platform="windows")  # '/D'
to_portable_path("\\\\server\\share\\dir", platform="windows")  # '//server/share/dir'
to_portable_path(None)  # '' (<Not A Path>)

# Values with no faithful counterpart are refused, never rewritten into another path.
try:
    from_portable_path("/home/lvuser", platform="windows")
except PortablePathError:
    ...
```

The rules below are checked against path values in files shipped with LabVIEW 2026
(`tests/fixtures/labview2026_paths.json` records each value with the file and setting it
was found in; the NI files themselves are not copied).
No shipped file holds a bare drive or a UNC value, so the `/D` and `//server/share/dir`
rows are covered by synthetic tests that follow the same convention:

| Stored value                     | Windows                        | POSIX                            |
| -------------------------------- | ------------------------------ | -------------------------------- |
| `/C/Program Files (x86)/Arduino` | `C:\Program Files (x86)\Arduino` | `/C/Program Files (x86)/Arduino` |
| `/c/ni-rt/startup`               | `c:\ni-rt\startup`             | `/c/ni-rt/startup`               |
| `/D`                             | `D:\`                          | `/D`                             |
| `//server/share/dir`             | `\\server\share\dir`           | `//server/share/dir`             |
| `../builds/Main Application`     | `..\builds\Main Application`   | `../builds/Main Application`     |
| `/home/lvuser/natinst/bin`       | `PortablePathError`            | `/home/lvuser/natinst/bin`       |
| empty                            | `NotAPathError`                | `NotAPathError`                  |

- The drive letter keeps its case, so a value in normal form (no trailing slash,
  repeated separator or `.` component, as LabVIEW writes it) round-trips exactly.
- A value already in native Windows form (`C:\NI Installers`), which some NI files
  store, is accepted as is when reading on Windows.
- On POSIX the stored form is already native and is parsed unchanged. A one-letter
  first directory is therefore ambiguous: `/C/x` reads as the drive `C:` on Windows
  and as the directory `/C/x` on POSIX. Pick `platform` for the system that will
  use the path.
- `PortablePathError` is raised for a POSIX absolute path read as Windows, a
  drive-relative `C:file`, a rooted Windows path without a drive (`\dir`), a UNC
  path without a share and a `\\?\` device path.
- A `str` is parsed with the flavor of `platform`; a `PurePath` keeps its own
  flavor, and only a relative one may be carried to the other flavor.
- Text is normalised by `pathlib`: repeated separators collapse, a trailing slash and
  `.` components are dropped, so `/C/x/` writes back as `/C/x`. A backslash inside a
  value read on Windows is a separator (`/C/x\y` reads as `C:\x\y`).
- The sibling `lvconfig` library (0.3.0 and later) gives the same results on drive,
  UNC and relative values in normal form, and refuses the same values lvpath refuses
  (`C:file`, `D:`, `\dir`, `//server`, a POSIX absolute path on Windows). The one
  difference left: lvpath normalises text through `pathlib`, where lvconfig only
  swaps separators.

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

Installing the package provides an `lvpath` command for the portable string form and
the flattened form.

```
# A stored LabVIEW path string to a native path, and back.
lvpath to-native --platform windows "/C/Program Files (x86)/Arduino"
# C:\Program Files (x86)\Arduino
lvpath to-labview --platform windows "C:\DIR1\DIR2"
# /C/DIR1/DIR2

# Decode the NI C:\File flattened example into a path.
lvpath decode --platform windows 505448300000000b0000000201430466696c65
# C:\file

# Encode a path into its flattened hex form.
lvpath encode --platform windows "C:\file"
# 505448300000000b0000000201430466696c65

lvpath --version
```

`lvpath decode` accepts hex with or without spaces. `lvpath to-labview ""` prints an
empty line, the `<Not A Path>` value, while `lvpath to-native ""` is an error. Errors
are written to standard error and the command exits with status 1. Output is UTF-8.
A value that starts with `-` goes after `--`. Under Git Bash on Windows, set
`MSYS_NO_PATHCONV=1` so the shell passes POSIX-looking arguments such as `/C/x`
unchanged. Run `lvpath --help` for the full usage.

## Covered conventions

LabVIEW's `Path To String` and `String To Path` render and parse a path in the
standard textual form of a host platform. `to_os_path`, `to_lv_path` and `path_kind`
model that native textual form (so `to_os_path("/C/foo", platform="windows")` is the
rooted Windows path `\C\foo`; read stored values with `from_portable_path` instead):

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
- It does not expand LabVIEW symbolic path prefixes such as `<vilib>` or
  `<instrlib>`, and it does not resolve a relative stored value against the file
  it came from.

## Why

LabVIEW uses two text forms for a path: the native form of its host platform for
`Path To String` / `String To Path`, and a platform-independent form (`/C/DIR1/DIR2`
for `C:\DIR1\DIR2`) when it writes a path into configuration and project files. Read
with plain string handling, the stored form names the wrong file on Windows, and a
native string only means something together with the platform convention it was
written in, so round-tripping LabVIEW path data in Python needs explicit,
platform-aware handling.

The standard library already does most of this. `pathlib`'s `PureWindowsPath` and
`PurePosixPath` are built to manipulate foreign-platform paths with no I/O, so they
cover the bulk of the separator and anchor handling on their own, and this library is
a thin wrapper over them rather than a reimplementation. What they do not know is the
genuinely LabVIEW-specific residue: the stored drive and UNC form (`/C/foo` to
`C:\foo` and back, through `from_portable_path` and `to_portable_path`), the empty
string standing for `<Not A Path>`, and LabVIEW's exact serialization rules. No PyPI package targets those conventions. `lvpath` adds exactly
that layer on top of `pathlib`, with a small, typed, zero-dependency surface.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

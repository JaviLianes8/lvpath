# lvpath guide

LabVIEW keeps a path in three forms. lvpath converts each of them to and from
`pathlib.PurePath` without touching the file system:

| Form | Where LabVIEW uses it | lvpath |
| --- | --- | --- |
| Portable text, `/C/DIR1/DIR2` | path values in `.ini` and `.lvproj` files | `from_portable_path`, `to_portable_path` |
| Native text, `C:\DIR1\DIR2` | `Path To String`, `String To Path` | `to_os_path`, `to_lv_path`, `path_kind` |
| Flattened bytes, `PTH0...` | `Flatten To String`, VI files, datalogs | `from_flat_path`, `to_flat_path`, `FlatPath` |

## The platform argument

Every conversion takes `platform`: `"windows"` or `"posix"` in any letter case, a
`Platform` member, or `None` for the system running the code. A `str` argument is
parsed with that flavor. A `PurePath` argument keeps its own flavor; when `platform`
names the other flavor, only a relative path may cross, and a component holding a
backslash or a colon may not cross to Windows.

```pycon
>>> from pathlib import PurePosixPath, PureWindowsPath
>>> from lvpath import Platform, to_lv_path
>>> to_lv_path(PureWindowsPath("reports\\q1.txt"), platform="posix")
'reports/q1.txt'
>>> to_lv_path(PureWindowsPath("C:/x"), platform=Platform.POSIX)
Traceback (most recent call last):
...
lvpath.PortablePathError: cannot carry the anchored path 'C:\\x' to the PurePosixPath flavor

```

## Portable text form

When LabVIEW writes a path value into a configuration or project file it uses a
platform-independent text: a Windows drive becomes a leading one-letter component, every
separator is `/`, a UNC share keeps its leading `//` and the empty string is
`<Not A Path>`.

| Stored value | `platform="windows"` | `platform="posix"` |
| --- | --- | --- |
| `/C/Program Files (x86)/Arduino` | `C:\Program Files (x86)\Arduino` | unchanged |
| `/c/ni-rt/startup` | `c:\ni-rt\startup` | unchanged |
| `/D` | `D:\` | unchanged |
| `//server/share/dir` | `\\server\share\dir` | unchanged |
| `../builds/Main Application` | `..\builds\Main Application` | unchanged |
| `/home/lvuser/natinst/bin` | `PortablePathError` | unchanged |
| empty | `NotAPathError` | `NotAPathError` |

```pycon
>>> from lvpath import from_portable_path, to_portable_path
>>> from_portable_path("/D", platform="windows")
PureWindowsPath('D:/')
>>> to_portable_path("\\\\server\\share\\dir", platform="windows")
'//server/share/dir'
>>> to_portable_path("C:file", platform="windows")
Traceback (most recent call last):
...
lvpath.PortablePathError: 'C:file' is drive-relative and has no portable form

```

- The drive letter keeps its case, so a value in the normal form LabVIEW writes (no
  trailing slash, repeated separator or `.` part) round-trips exactly.
- A value already in native Windows form (`C:\NI Installers`), which some NI files
  store, is accepted as is when reading on Windows.
- On POSIX the stored form is already native and is parsed unchanged, so `/C/x` is a
  drive on Windows and a directory on POSIX. Pick `platform` for the system that will
  use the path.
- Refused with `PortablePathError`: a POSIX absolute path read as Windows, a malformed
  drive (`/C:/x`), a drive-relative `C:file`, a rooted path without a drive (`\dir`),
  a UNC path without a share and the `\\?\` and `\\.\` device forms.
- `pathlib` normalises the text: repeated separators collapse, a trailing slash and
  `.` parts are dropped, and a backslash read on Windows is a separator.
- An empty `PurePath` is pathlib's current directory and writes as `"."`; `None` and
  `""` write as `""`.

The table rows are checked against values found in files shipped with LabVIEW 2026
(`tests/fixtures/labview2026_paths.json` records each value with its file and setting,
not the file text). No shipped file holds a bare drive or a UNC value; those rows are
covered by tests written by hand that follow the same convention.

## Native text form

`to_os_path` and `path_kind` read the text of a host platform, `to_lv_path` writes it.
On Windows forward slashes are accepted, and only a drive with a root or a UNC share is
absolute, so `C:file` and `\dir` count as relative, as `pathlib` decides.

```pycon
>>> from lvpath import NotAPathError, PathKind, path_kind, to_os_path
>>> path_kind("C:file", platform="windows")
<PathKind.RELATIVE: 'relative'>
>>> to_os_path("/C/foo", platform="windows")
PureWindowsPath('/C/foo')
>>> try:
...     to_os_path("", platform="posix")
... except NotAPathError as error:
...     print(error)
LabVIEW not-a-path has no OS path

```

Read stored values with `from_portable_path`: `to_os_path` keeps `/C/foo` as the rooted
Windows path `\C\foo`.

## Flattened form

`Flatten To String` writes a path as `PTH0`, a u32 byte count of the rest, a u16 path
type, a u16 component count and one length-prefixed ASCII string per component, all
big-endian. `FlatPath`, `parse_flat_path` and `build_flat_path` read and write that
container exactly and keep any path type as a number.

```pycon
>>> from lvpath import FlatPath, build_flat_path, from_flat_path, parse_flat_path, to_flat_path
>>> parse_flat_path(build_flat_path(1, ["", "", "NI_MDF.lvlib"]))
FlatPath(path_type=1, components=('', '', 'NI_MDF.lvlib'))
>>> from_flat_path(build_flat_path(1, ["", "", "NI_MDF.lvlib"]), platform="windows")
PureWindowsPath('../../NI_MDF.lvlib')
>>> from_flat_path(build_flat_path(0, []), platform="posix")
PurePosixPath('/')
>>> from_flat_path(build_flat_path(0, ["<vilib>", "Utility"]), platform="posix")
Traceback (most recent call last):
...
lvpath.FlatPathError: symbolic path prefix '<vilib>' has no PurePath meaning

```

`from_flat_path` and `to_flat_path` interpret two path types:

- `0`, absolute (`FlatPathType.ABSOLUTE`). On Windows the first component is the drive
  letter without its colon; on POSIX the components follow the root, and no component
  at all is `/`. That empty absolute path has no Windows `PurePath`.
- `1`, relative (`FlatPathType.RELATIVE`). No component at all is `.`.
- In both, an empty component means one level up, `..` in text.

Everything else raises `FlatPathError` in the bridge: another path type (LabVIEW 2026
stores one record of type `2`, with no component, in `resource/labview.rsc`; its
meaning is not established), a symbolic first component such as `<vilib>`, a first
Windows component that is not one letter, a literal `.` or `..` component, a component
holding `/` (or `\` or `:` on Windows), UNC and driveless rooted Windows paths,
drive-relative paths and POSIX paths starting with `//`. Components are ASCII, at most
255 characters, and at most 65535 of them.

### Ground truth for the flattened form

- NI's flattened-data page gives `C:\File` as
  `5054 4830 0000 000B 0000 0002 0143 0466 696C 65` and names type `0` only. Its bytes
  spell `file` in lower case. `tests/test_sources_truth.py` reads the example from a
  copy fetched by `scripts/fetch_sources.py` (not committed; `MANIFEST.json` keeps the
  URL, date and SHA-256).
- `scripts/scan_labview_paths.py` walked a LabVIEW 2026 install on 2026-10-15 and found
  321,686 records of type `0`, 27,879 of type `1` and one of type `2`. Of the 24,024
  relative links that start with empty components, 21,765 name an existing file when
  each empty component is read as one level up from the file holding the link; no
  record holds a literal `..`. Eleven chosen records, with file and offset, are in
  `tests/fixtures/labview2026_flat.json`.

## Errors

| Exception | Base | Raised for |
| --- | --- | --- |
| `NotAPathError` | `ValueError` | the empty `<Not A Path>` value read as an OS path |
| `PortablePathError` | `ValueError` | a value with no faithful counterpart in the portable or native form |
| `FlatPathError` | `ValueError` | malformed `PTH0` bytes, bad components, a path the bridge cannot represent |
| `ValueError` | | an unknown `platform` name |
| `TypeError` | | an argument of the wrong type (a path that is not `str` or `PurePath`, bytes that are not bytes-like, a non-integer path type) |

A message quotes at most 40 characters of any value and states the full length of a
longer one. The three exception classes report their module as `lvpath`.

```pycon
>>> from lvpath import FlatPathError, PortablePathError
>>> try:
...     to_portable_path("C:" + "x" * 1000, platform="windows")
... except PortablePathError as error:
...     print(error)
'C:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' (first 40 of 1002 characters) is drive-relative and has no portable form
>>> issubclass(FlatPathError, ValueError)
True

```

## Command line

```console
$ lvpath to-native --platform windows //server/share/dir
\\server\share\dir
$ lvpath to-labview --platform posix ''

$ lvpath decode --platform posix '50544830 00000007 0001 0002 00 0161'
../a
$ lvpath to-native --platform windows /home/lvuser
lvpath: '/home/lvuser' is a POSIX absolute path with no Windows equivalent
```

Output is UTF-8. A refused value prints one line on standard error and exits with
status 1; a usage mistake prints the usage and one line and exits with status 2; a
closed output pipe exits with status 1 quietly. A value starting with `-` goes after
`--`. Under Git Bash on Windows set `MSYS_NO_PATHCONV=1` so `/C/x` reaches lvpath
unchanged.

## Upgrading from 0.3

The public names and signatures are the same. Behaviour that changed:

- An empty flattened component now decodes as `..` (0.3 dropped it, so
  `('', 'x.vi')` became `x.vi`), and `..` now encodes as an empty component (0.3 wrote
  the two dots).
- `from_flat_path` now refuses what it used to misread: symbolic `<vilib>` prefixes,
  a first Windows component that is not a drive letter, literal `.` and `..`
  components and components holding separators. `to_flat_path` refuses POSIX paths
  starting with `//`.
- A `PurePath` passed with `platform=None` keeps its own flavor in `to_lv_path` and
  `to_flat_path` (0.3 re-read it with the running system's flavor), and an anchored
  path is no longer carried to the other flavor.
- `FlatPath` checks its fields when built: a non-integer type or a non-`str` component
  raises `TypeError`, a non-ASCII or over-long component `FlatPathError` (0.3 failed
  later, in `to_bytes`); components are stored as a tuple.
- Non-ASCII flattened bytes raise `FlatPathError` (0.3 let `UnicodeDecodeError`
  through). `bytearray` and `memoryview` are accepted wherever bytes are.
- A `platform` that is not a `str`, a `Platform` or `None` raises `TypeError` (0.3:
  `AttributeError`).
- Messages are bounded and some are worded differently; the CLI gained
  `python -m lvpath`, exit status 2 with a short line for usage mistakes, and a quiet
  exit on a closed pipe.

## What it does not do

- No file system access, no symbolic links, no `.`/`..` resolution beyond `pathlib`.
- No classic Mac OS colon paths.
- No expansion of symbolic prefixes such as `<vilib>` and no resolution of a relative
  value against the file it came from.

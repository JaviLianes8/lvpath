# lvpath

Convert LabVIEW path values to and from Python `pathlib` paths, in all three forms
LabVIEW uses: the portable text it writes into configuration and project files
(`/C/DIR1/DIR2`), the native text of `Path To String`, and the flattened `PTH0` bytes
of `Flatten To String`. Typed, no dependencies, Python 3.10 to 3.14.

## Install

```
pip install lvpath
```

## Quick start

Read a path value stored in an `.ini` or `.lvproj` file, and write one back:

```pycon
>>> from lvpath import from_portable_path, to_portable_path
>>> from_portable_path("/C/Program Files (x86)/Arduino", platform="windows")
PureWindowsPath('C:/Program Files (x86)/Arduino')
>>> from_portable_path("../builds/Main Application", platform="windows")
PureWindowsPath('../builds/Main Application')
>>> to_portable_path("C:/DIR1/DIR2", platform="windows")
'/C/DIR1/DIR2'
>>> to_portable_path(None)
''

```

Decode the flattened bytes of a LabVIEW path, such as NI's `C:\File` example:

```pycon
>>> from lvpath import from_flat_path, parse_flat_path, to_flat_path
>>> golden = bytes.fromhex("505448300000000b0000000201430466696c65")
>>> parse_flat_path(golden)
FlatPath(path_type=0, components=('C', 'file'))
>>> from_flat_path(golden, platform="windows")
PureWindowsPath('C:/file')
>>> to_flat_path("C:/file", platform="windows") == golden
True
>>> from_flat_path(to_flat_path("../lib/x.vi", platform="posix"), platform="posix")
PurePosixPath('../lib/x.vi')

```

Work with the native text form and LabVIEW's `<Not A Path>` (the empty string):

```pycon
>>> from lvpath import path_kind, to_lv_path, to_os_path
>>> to_os_path("C:\\Users\\test\\data.txt", platform="windows")
PureWindowsPath('C:/Users/test/data.txt')
>>> to_lv_path("logs/run.txt", platform="windows")
'logs\\run.txt'
>>> path_kind("", platform="posix")
<PathKind.NOT_A_PATH: 'not_a_path'>

```

Every `platform` argument takes `"windows"`, `"posix"`, a `Platform` member, or `None`
for the system running the code. Values with no faithful counterpart raise a typed
error (`PortablePathError`, `FlatPathError`, `NotAPathError`) instead of being turned
into a different path.

## Command line

```console
$ lvpath to-native --platform windows '/C/Program Files (x86)/Arduino'
C:\Program Files (x86)\Arduino
$ lvpath to-labview --platform windows 'C:\DIR1\DIR2'
/C/DIR1/DIR2
$ lvpath decode --platform windows 505448300000000b0000000201430466696c65
C:\file
$ lvpath encode --platform posix ../lib/x.vi
505448300000000e0001000300036c696204782e7669
```

`python -m lvpath` runs the same command. Refused values exit with status 1, usage
mistakes with status 2. Run `lvpath --help` for every option.

## Why

LabVIEW writes one path in different forms depending on where it goes, and none of
them reads correctly with plain string handling: `/C/DIR1/DIR2` names the wrong file on
Windows, a native string means something only with the platform it was written on,
and the flattened form needs the `PTH0` layout. `pathlib`'s `PureWindowsPath` and
`PurePosixPath` already handle foreign-platform paths with no file access, so lvpath is
a thin layer on top of them that adds only the LabVIEW part: the portable drive and UNC
form, `<Not A Path>`, and the flattened container, including the rule that an empty
flattened component means one level up.

The conversions are checked against path values in files shipped with LabVIEW 2026,
against flattened paths LabVIEW 2026 stored in its own installed files, and against
the example on NI's public flattened-data page.

## Documentation

- [Guide](https://github.com/JaviLianes8/lvpath/blob/main/GUIDE.md): every rule, the
  errors, the command line and upgrading from 0.3.
- [Changelog](https://github.com/JaviLianes8/lvpath/blob/main/CHANGELOG.md)

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/lvpath/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

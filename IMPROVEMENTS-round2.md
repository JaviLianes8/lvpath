# Improvements round 2: the portable path form

The README promised that lvpath converts LabVIEW's platform-independent path
strings such as `/C/DIR1/DIR2` to `C:\DIR1\DIR2`, but no function did:
`to_os_path("/C/foo", platform="windows")` returned the rooted Windows path
`\C\foo`. This round implements that conversion, which is the library's main
purpose, and makes every README claim match the code.

## Ground truth

LabVIEW writes path values into configuration (`.ini`) and project (`.lvproj`)
files in a portable form. An NI forum thread ("Config files and the PATH") shows
`C:\DIR1\DIR2` saved as `/C/DIR1/DIR2`. Files shipped with LabVIEW 2026 confirm
the form and its variants:

- `project/Hobbyist/LINX Firmware Wizard Config.ini`:
  `ArduinoBasePath = "/C/Program Files (x86)/Arduino"` (upper-case drive, spaces).
- `resource/Framework/Providers/lvrealtime/default ini/Def_RTCommon.ini`:
  `RTTarget.VIPath=/c/ni-rt/startup` (lower-case drive, kept as written).
- `resource/Framework/Providers/lvrealtime/default ini/Def_LINXprovider.ini`:
  `RTTarget.VIPath="/home/lvuser/natinst/bin"` (a Linux target, POSIX absolute).
- `.lvproj` build specifications: `Type="Path"` values such as
  `../builds/NI_AB_PROJECTNAME/Main Application`, `vi.lib/ActorFramework`,
  `/C/Users/lvadmin/Documents/LabVIEW Data/InstCache` and empty values.
- `Def_RemoteWindowsCommon.ini` stores some values in native Windows form
  (`c:\NI Installers`), so a reader must accept that too.

No file on the reference machine holds a UNC value; the `//server/share` form
follows the same convention and matches the sibling `lvconfig` library.

## Ranked improvements

1. **Read the portable form (core).** `from_portable_path(text, platform=...)`
   returns a `PureWindowsPath` or `PurePosixPath`: `/C/x` to `C:\x`, `/D` to
   `D:\`, `//server/share/x` to a UNC path, `a/b` and `../a` to relative paths.
   Native Windows text is accepted as is.

2. **Write the portable form.** `to_portable_path(path, platform=...)` is the
   exact inverse, so every stored value round-trips byte for byte, including the
   case of the drive letter.

3. **Not-A-Path.** The empty value raises `NotAPathError` when read, and `None`
   or `""` writes back as `""`, matching the existing textual surface.

4. **Honest errors.** `PortablePathError` refuses values with no faithful
   counterpart rather than inventing one: a POSIX absolute path read on Windows,
   a drive-relative `C:file`, a rooted path without a drive, a UNC path without a
   share and a `\\?\` device path.

5. **Consistency with lvconfig.** Same outputs as `lvconfig`'s
   `to_labview_path` / `from_labview_path` on drive, UNC and relative values,
   pinned by a test over lvconfig's own vectors. lvpath stays zero-dependency and
   does not import it. Two deliberate differences: lvpath refuses the lossy cases
   above where lvconfig rewrites them (`C:file` to `/C/file`, `/home/x` to
   `\home\x` on Windows), and a bare share `//srv/sh` renders with `pathlib`'s
   trailing backslash (`\\srv\sh\`), the same path.

6. **CLI.** `lvpath to-native` and `lvpath to-labview` beside `decode` and
   `encode`, with runnable examples in `--help`; errors go to stderr with exit 1.

7. **Real fixtures and contracts.** A verbatim excerpt of LabVIEW 2026 path
   lines with their source files, checked in both directions, on both flavors and
   through a round trip, tied to the NI `PTH0` golden vector. A real end-to-end
   test installs the package and drives the `lvpath` console script.

8. **Honest README.** Remove the implication that `to_os_path` translates
   `/C/foo`, document the portable rules in a table, and state the one inherent
   ambiguity: a one-letter first directory (`/C/x`) is a drive on Windows and a
   directory on POSIX.

## Deferred

- A `portable_path_kind` classifier. `path_kind` classifies native text; the
  portable kind follows from `from_portable_path(...).is_absolute()`.
- Expanding symbolic prefixes such as `<vilib>` and resolving relative stored
  values against their file. These need context the string alone does not carry.

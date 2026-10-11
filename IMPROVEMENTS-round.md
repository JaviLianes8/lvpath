# Improvements round: the PTH0 flattened path form

This round adds the one capability the library explicitly called out as out of
scope: the binary flattened form LabVIEW produces with `Flatten To String` /
`Unflatten From String` for the Path data type. The existing textual
`Path To String` / `String To Path` surface stays untouched and the new API is
purely additive.

## Ground truth

The authoritative reference is the NI documentation of flattened data and its
worked example: the absolute path `C:\File` flattens (big-endian) to

```
50 54 48 30  00 00 00 0B  00 00  00 02  01 43  04 66 69 6C 65
```

Decoded: `"PTH0"` signature, total length `0x0000000B` (11, the byte count that
follows this field), path type `0x0000` (absolute), component count `0x0002`,
then two Pascal strings (one length byte, then that many bytes): `01 43` = `"C"`
and `04 66696C65` = `"file"`. This exact byte string is the golden contract
vector and is round-tripped byte for byte in both directions by the tests.

The NI prose names the path `C:\File` while the bytes spell `file` in lower
case; the bytes are authoritative, so the library reads and reproduces the bytes
exactly rather than the prose.

## Ranked improvements

1. **Parse and build the PTH0 flattened form (core).** A faithful codec for the
   documented container: validate the `PTH0` signature, read the big-endian u32
   total length and check it against the real body size, read the u16 path type
   and u16 component count, then the length-prefixed (Pascal) components. Build
   is the exact inverse and reproduces the golden vector byte for byte.

2. **A typed result.** `FlatPath` is a frozen dataclass of `path_type: int` and
   `components: tuple[str, ...]` with `to_bytes()` and `from_bytes()`. It keeps
   the raw numeric path type so any flattened path round-trips losslessly, even
   when its type code is one this library does not interpret.

3. **Honest path-type handling, no invented codes.** Only two path type codes
   are documented and verifiable: `0` absolute and `1` relative, exposed as
   `FlatPathType`. UNC and the empty / not-a-path forms have their own codes that
   the public NI documentation does not state, so the library does not guess
   them: the low-level codec still round-trips their bytes faithfully, but the
   PurePath bridge refuses an un-interpretable type code with a clear error
   rather than inventing a meaning.

4. **Conversion to and from `pathlib.PurePath`.** `to_flat_path` encodes an OS
   path (or `str`) to PTH0 bytes and `from_flat_path` decodes PTH0 bytes back to
   a `PurePath` of the chosen platform flavor, reusing the existing platform
   resolution. Absolute Windows paths store the drive letter (without its colon)
   as the first component, matching the golden vector; absolute POSIX paths store
   the components after the leading root.

5. **Round-trip guarantees.** `FlatPath` -> bytes -> `FlatPath` and OS path ->
   bytes -> OS path both round-trip, asserted against the NI golden vector and
   against generated paths on both platform flavors.

6. **Honest errors.** `FlatPathError` covers a bad signature, a truncated
   stream, a declared length that disagrees with the body, a component that
   overruns the buffer, and an un-interpretable path type in the PurePath bridge.
   Every failure names what was wrong; nothing is silently guessed.

7. **A CLI.** `lvpath` gains `decode` (hex of PTH0 bytes to an OS path) and
   `encode` (an OS path to PTH0 hex), plus `--version`. Help text carries
   runnable examples; errors go to stderr with exit code 1.

8. **Docs and contract tests.** README gains a flattened-form section, the
   public-API contract test lists the new names, and the changelog records the
   addition. The package minor version is bumped for the additive surface.

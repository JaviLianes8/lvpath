# lvpath 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.1, b0f29e1)
- [x] Baseline gates run on 0.3.1
- [x] Real LabVIEW 2026 ground truth: flattened paths stored in the install's own files (item 7)
- [x] Public source fetched (NI flattened data page), manifest tracked (item 7)
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.3.1 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19): five lenses done; reviewer pending
- [x] Gates (item 15)
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Scorecard

| # | Item | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | API reviewed for stability | PASS | same 17 names and parameters as 0.3.1 (annotations widened only); every behaviour change in CHANGELOG 1.0.0 and the guide's identical upgrade list, confirmed claim by claim against PyPI 0.3.1; lens a PASS at round 3 |
| 2 | `__all__` exact | PASS | `test_contract::test_all_lists_exactly_the_public_api` |
| 3 | Docstrings with runnable examples | PASS | every public name and `FlatPath` member has `>>>`; every module doctested; README and GUIDE `pycon` blocks and `console` transcripts run in `test_docs` |
| 4 | Typed end to end | PASS | `mypy --strict src tests` clean; `py.typed` shipped; `get_type_hints` on every public callable |
| 5 | Typed, documented, safe errors | PASS | GUIDE error table; messages quote at most 40 characters of a value; CLI lines at most 200 |
| 6 | Contract asserts the full promise | PASS | 372 tests: a promise test per public name, LabVIEW and NI ground truth, fuzz, CLI in process and by subprocess on the wheel, and the contracts from the author round and the blind lens e round |
| 7 | Real ground truth | PASS | 349,566 `PTH0` records LabVIEW 2026 stored in its install, 11 chosen ones in a fixture, full sweep opt-in; NI page fetched 2026-10-15; 0.3.1 fixture of values from LabVIEW 2026 files |
| 8 | Real e2e incl. PyPI upgrade | PASS | wheel in a throwaway venv driven by subprocess (`conftest.py`, `test_cli_e2e*.py`); PyPI 0.3.1 upgraded in place by the author and by lens d, every change-list claim confirmed |
| 9 | Seeded fuzz, no crash, hang or blow-up | PASS | `test_fuzz.py` (20,000 mutated byte strings, 100,000 random text calls, 5,000 round trips, six scaling checks); lens c rounds: 200,000 + 60,000 + 32,672 seeded cases, 1,500 subprocess CLI runs, every dimension linear; PASS at round 3 |
| 10 | Every interpreter | PASS | sdist suite with `src` removed against the wheel: author on 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t; lens d on 3.10.22, 3.11.13, 3.12.15, 3.13.16, 3.14.2, 3.14.8t |
| 11 | README | PASS | `twine check --strict` PASSED; absolute links tested; problem, why, install, quick start, GUIDE and CHANGELOG links |
| 12 | CHANGELOG dated 1.0.0 | PASS | `## [1.0.0] - 2026-10-15` |
| 13 | pyproject | PASS | 1.0.0, Production/Stable, 3.10 to 3.14, MIT, Homepage/Source/Issues/Changelog, keywords, `dependencies = []` (`test_packaging`) |
| 14 | sdist and wheel contents | PASS | wheel: package, `py.typed`, LICENSE, metadata; sdist: src, tests, fixtures, sources manifest only, docs |
| 15 | Gates exit 0 alone | PASS | `ruff format --check .`, `ruff check .`, `mypy --strict src`, `pytest` (on Elena's PC at 46d9403: 357 passed, 4 skipped, wheel end-to-end included) |
| 16 | Independent reviewer | pending | |
| 17 | PR, trace guard | pending | |
| 18 | Mutation round | PASS | author: 47 mutations, all killed (3 after new contracts); blind lens e: 40 mutations, 33 killed, 7 survivors closed by contracts and re-verified killed; tables below |
| 19 | Five QA lenses | PASS | a (round 3), b (round 1), c (round 3), d (round 1) PASS; e FAIL until its seven contracts were added, all its mutants then killed |

## Baseline on 0.3.1 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .`, `mypy --strict src tests` | exit 0 |
| `pytest` | 196 passed |
| `pytest --doctest-modules src` | no doctests at all |

## Ground truth (item 7)

- LabVIEW 2026 Community 26.3.1f1 is installed on this PC, but on 2026-10-15 it could not
  be driven through its ActiveX server: at start-up its NI User Account sign-in dialog
  reported a server error and the COM class never registered. Ground truth was taken from
  files LabVIEW itself wrote instead.
- `scripts/scan_labview_paths.py` walked the install and found every complete `PTH0`
  record LabVIEW saved into its VIs, controls, libraries and resource files, files over
  50 MB skipped (`LabVIEW.exe`, `resource/libcef.dll`, the object cache
  `VIObjCache/26.0.0r0/objFileDB.vidb` whose records include corrupted fragments): 321,686 of
  path type 0, 27,879 of type 1, one of type 2 (no component, in `resource/labview.rsc`).
  24,024 relative links start with empty components; 21,765 of them name an existing file
  when each empty component is read as one level up from the file holding the link. No
  record holds a literal `.` or `..`, and no component in the scanned files is non-ASCII. Absolute records start
  with a drive letter (`C`, `c`, `w`), a POSIX name (`usr`) or a symbolic prefix
  (`<vilib>`, `<resource>` and others); 2,534 absolute records have no component.
- `tests/fixtures/labview2026_flat.json` keeps the scan summary and eleven chosen records
  (file, offset, bytes); `tests/test_real_labview_flat.py` checks them, and with
  `LVPATH_LABVIEW_ROOT` set it re-reads the whole install: every record round-trips byte
  for byte through `FlatPath` and every relative link through `from_flat_path` and
  `to_flat_path` (run on 2026-10-15: passed, more than 300,000 records).
- NI's flattened-data page, fetched 2026-10-15 by `scripts/fetch_sources.py` (copy not
  committed, `tests/fixtures/sources/MANIFEST.json` holds URL, date, size, SHA-256): its
  `C:\File` example is parsed from the page by `tests/test_sources_truth.py`. The page names
  type `0` only and its bytes spell `file` in lower case; 0.3.1 called the relative code
  documented, which it is not: the scan above is now its evidence.
- The 0.3.1 fixture of portable values found in LabVIEW 2026 `.ini` and `.lvproj` files is
  kept and still checked in both directions.

## API review (item 1)

The seventeen public names of 0.3.1 keep their signatures and defaults. Behaviour changes,
all in CHANGELOG 1.0.0 and the guide's upgrade section:

- Flattened up-levels: an empty component decodes as `..`, and `..` encodes as an empty
  component (0.3.1 silently dropped empty components, so real LabVIEW links decoded to the
  wrong path).
- `from_flat_path` refuses symbolic prefixes, non-letter Windows drives, the empty absolute
  path on Windows, literal dots and components with separators; `to_flat_path` refuses POSIX
  `//` paths and rooted driveless Windows paths.
- A `PurePath` keeps its own flavor with `platform=None` in `to_lv_path` and `to_flat_path`;
  anchored paths and components with a colon do not cross flavors.
- `FlatPath` validates its fields at construction and stores components as a tuple; non-ASCII
  bytes raise `FlatPathError`; `bytearray` and `memoryview` are accepted.
- Wrong argument types raise `TypeError` with a short message; messages are bounded; the
  exception classes report module `lvpath`.
- `python -m lvpath`; the command exits 2 for usage mistakes with bounded lines and 1 quietly
  on a closed pipe.

## Upgrade from PyPI 0.3.1 (item 8)

`pip install lvpath==0.3.1` from PyPI into a fresh venv, a 64-call battery run, the 1.0.0
wheel installed over it with `--upgrade`, the battery run again: 38 results identical, 26
different, every one of them a change listed above (up-levels, refusals of misread values,
`TypeError` for a non-string platform, `FlatPathError` for non-ASCII bytes, components as a
tuple, construction-time checks, reworded and bounded messages).

## Author mutation round (item 18)

Each mutation was applied alone to a fresh clone of the branch, the suite run with `-x`
(the two wheel end-to-end modules deselected, the CLI is exercised in process), and the
clone restored; the suite was green before and after. First run: 47 mutations, 43 killed, 3
survived (M20, M45, M46) and one (M47) was a broken mutation; contracts were added for the
three survivors and M47 was rewritten, and the rerun killed all four.

| Id | Mutation | File | Caught by |
| --- | --- | --- | --- |
| M01 | up-level not encoded | `_flatbridge.py` | `test_contract_one.py::test_up_levels_map_both_ways` |
| M02 | up-level decoded as `.` | `_flatbridge.py` | `test_contract_one.py::test_up_levels_map_both_ways` |
| M03 | relative encoded as absolute | `_flatbridge.py` | `test_contract_one.py::test_up_levels_map_both_ways` |
| M04 | drive keeps its colon | `_flatbridge.py` | `test_cli.py::test_decode_and_encode_still_work` |
| M05 | UNC accepted | `_flatbridge.py` | `test_contract_one.py::test_unflattenable_paths_are_refused[UNC]` |
| M06 | drive-relative accepted | `_flatbridge.py` | `test_contract_one.py::test_unflattenable_paths_are_refused[drive-relative]` |
| M07 | POSIX `//` accepted | `_flatbridge.py` | `test_contract_one.py::test_unflattenable_paths_are_refused[//]` |
| M08 | POSIX root kept as component | `_flatbridge.py` | `test_flatten.py::test_posix_absolute_round_trips_via_the_bridge` |
| M09 | unknown type decoded as relative | `_flatbridge.py` | `test_flatten.py::test_uninterpretable_type_code_is_refused_by_the_bridge` |
| M10 | symbolic prefix accepted | `_flatbridge.py` | `test_docs.py::test_guide_examples_run_and_print_what_they_show` |
| M11 | empty absolute accepted on Windows | `_flatbridge.py` | `test_fuzz.py::test_mutated_flattened_bytes_parse_or_raise_flat_path_error` |
| M12 | multi-letter drive accepted | `_flatbridge.py` | `test_fuzz.py::test_mutated_flattened_bytes_parse_or_raise_flat_path_error` |
| M13 | literal `..` accepted | `_flatbridge.py` | `test_contract_one.py::test_literal_dots_and_slashes_in_components_are_refused[..]` |
| M14 | colon allowed on Windows | `_flatbridge.py` | `test_contract_one.py::test_windows_special_characters_are_refused_only_on_windows[a:b]` |
| M15 | slash allowed on POSIX | `_flatbridge.py` | `test_contract_one.py::test_literal_dots_and_slashes_in_components_are_refused[a/b]` |
| M16 | length written little-endian | `_flatten.py` | `test_cli.py::test_decode_and_encode_still_work` |
| M17 | header read little-endian | `_flatten.py` | `test_cli.py::test_decode_and_encode_still_work` |
| M18 | declared length unchecked | `_flatten.py` | `test_fuzz.py::test_mutated_flattened_bytes_parse_or_raise_flat_path_error` |
| M19 | trailing bytes accepted | `_flatten.py` | `test_fuzz.py::test_mutated_flattened_bytes_parse_or_raise_flat_path_error` |
| M20 | overrun check off by one | `_flatten.py` | after a new contract: `test_contract_one.py::test_a_component_overrunning_by_one_byte_is_named_as_an_overrun` |
| M21 | non-ASCII bytes read as Latin-1 | `_flatten.py` | `test_contract_one.py::test_non_ascii_component_bytes_raise_flat_path_error` |
| M22 | signature unchecked | `_flatten.py` | `test_docs.py::test_module_doctests_pass[lvpath]` |
| M23 | short-header check off by one | `_flatten.py` | `test_fuzz.py::test_mutated_flattened_bytes_parse_or_raise_flat_path_error` |
| M24 | `bool` path type accepted | `_fields.py` | `test_contract_one.py::test_a_path_type_that_is_not_an_integer_is_a_type_error[True]` |
| M25 | u16 bound off by one | `_fields.py` | `test_contract_one.py::test_a_path_type_outside_u16_is_refused[65536]` |
| M26 | 256-character component accepted | `_fields.py` | `test_contract_one.py::test_component_limits_are_checked_at_construction` |
| M27 | component count off by one | `_fields.py` | `test_contract_one.py::test_component_limits_are_checked_at_construction` |
| M28 | `str` accepted as components | `_fields.py` | `test_contract_one.py::test_components_must_be_an_iterable_of_str[ab0]` |
| M29 | `memoryview` refused | `_fields.py` | `test_contract_one.py::test_bytes_like_input_is_read_and_text_is_refused` |
| M30 | portable drive lower-cased | `_portable.py` | `test_cli.py::test_to_native_converts_a_drive_path` |
| M31 | POSIX absolute accepted on Windows | `_portable.py` | `test_cli.py::test_every_help_example_runs_and_prints_what_it_states` |
| M32 | device prefix accepted | `_portable.py` | `test_portable.py::test_values_with_no_windows_equivalent_are_refused[device]` |
| M33 | UNC without share accepted | `_portable.py` | `test_portable.py::test_values_with_no_windows_equivalent_are_refused[//server-UNC]` |
| M34 | rooted driveless accepted | `_portable.py` | `test_cli.py::test_to_labview_errors_go_to_stderr` |
| M35 | empty `PurePath` not written as `.` | `_portable.py` | `test_portable.py::test_windows_path_writes_the_portable_string[.-.]` |
| M36 | not-a-path kind wrong | `_convert.py` | `test_convert.py::test_empty_string_is_not_a_path` |
| M37 | platform names case-sensitive | `_platform.py` | `test_contract_one.py::test_platform_names_are_case_insensitive_and_checked` |
| M38 | wrong error type for a platform | `_platform.py` | `test_contract_one.py::test_platform_names_are_case_insensitive_and_checked` |
| M39 | `PurePath` re-flavored with `platform=None` | `_coerce.py` | `test_contract_one.py::test_a_pure_path_keeps_its_flavor_and_only_relative_paths_cross` |
| M40 | anchored path crosses flavors | `_coerce.py` | `test_contract_one.py::test_a_pure_path_keeps_its_flavor_and_only_relative_paths_cross` |
| M41 | colon crosses to Windows | `_coerce.py` | `test_contract_one.py::test_a_pure_path_keeps_its_flavor_and_only_relative_paths_cross` |
| M42 | message bound lifted | `_text.py` | `test_docs.py::test_module_doctests_pass[lvpath._text]` |
| M43 | usage mistake exits 1 | `_cli.py` | `test_cli.py::test_a_missing_command_is_a_usage_error` |
| M44 | refused value exits 2 | `_cli.py` | `test_cli.py::test_to_native_errors_go_to_stderr` |
| M45 | spaces inside a hex pair rejected | `_cli.py` | after a new contract: `test_cli.py::test_hex_may_hold_spaces_anywhere` |
| M46 | CLI line bound lifted | `_cli.py` | after a new contract: `test_cli.py::test_every_error_line_is_at_most_200_characters` |
| M47 | `to-labview` output altered | `_cli.py` | `test_cli.py::test_to_labview_converts_a_unc_path` |

## Independent QA lenses (item 19)

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a. API and docs | 1 | a6126e0 | FAIL (2 medium, 9 low, info) | about 80 calls compared with PyPI 0.3.1, every example and transcript, strict consumer, pickles. Unlisted: `PurePath` input refused by `to_os_path`, `path_kind`, `from_portable_path`; `platform` checked first only in some functions; backslash crossing rule; `mmap`/`array` refused; `build_flat_path` splitting a `str`; `IntEnum` stored as `int`. Also CHANGELOG items 0.3.1 already did, `FlatPath` typing against its docstring, private `__module__` on public classes, quoted number in a message, GUIDE upgrade list shorter than CHANGELOG. Fixed in cf09a0c (path objects read again, platform first everywhere, any buffer read, one shared change list, `tests/test_contract_two.py`) |
| a. API and docs | 2 (new reviewer) | cf09a0c | FAIL (5 medium, 2 low, info) | every example and transcript, strict consumer, pickles both ways, about 100 calls against 0.3.1; the round 1 fixes confirmed. New: `from_flat_path` read the bytes before checking `platform`; text readers re-flavored a `PurePath` (different results on 3.10/3.11); the buffer claim of parity with 0.3.1 was wrong; five differences missing from the upgrade list; the 65,536-component remark wrong; LabVIEW's own `cintools/extcode.h` numbers the path types (2 not-a-path, 3 UNC) while `to_flat_path("")` wrote an empty relative path; a 0.3.1 pickle loaded an unnormalised `FlatPath`. Fixed in the next commit: not-a-path is type 2 both ways (`NotAPathError` on decode), one `PurePath` flavor rule everywhere, `__setstate__` normalises old pickles (tested with bytes written by PyPI 0.3.1), corrected change list |
| a. API and docs | 3 (new reviewer) | 8a88c94 | PASS (3 low, info) | gates on Elena's PC; about 110 calls against 0.3.1 confirming every change-list claim, identical on 3.10 to 3.14; README, GUIDE and docstring doctests and 8 transcripts through `lvpath` and `python -m lvpath`; strict consumer clean; pickles both ways for protocols 0, 2 and 5; rounds 1 and 2 fixed. Lows (one change-list sentence missing `from_portable_path` on POSIX, the `None` annotation of `to_flat_path`, an ambiguous name count) fixed in the next commit |
| b. Correctness and ground truth | 1 | eb4b81c | PASS (1 low, 2 info) | own `PTH0` parser and up-level resolver over the whole install with no size cut: 680,038 complete records, lvpath's parse, rebuild and `from_flat_path` on both flavors agree on every one (1,061 refused non-ASCII fragments, all in the object cache); the documented counts re-derived exactly; the 11 fixture records match file and offset; 1,533 portable values found independently in 286 `.ini`/`.lvproj` files with no difference; NI page re-fetched, same SHA-256; `extcode.h` order confirmed. Low: the 50 MB cut of the scan was not stated; info: `extcode.h` wording, the empty absolute path on Windows. All addressed in the next commit |
| c. Adversarial and robustness | 1 | 10445db | FAIL (1 medium, 4 low, info) | 200,000 seeded in-process fuzz cases over every public function (all outcomes documented errors), about 560 hostile-object probes, 11 shapes x 6 functions scaling linearly to 320k, 65,535 components in under 70 ms, 8 threads x 18,000 calls identical to serial, 400 random CLI runs by subprocess on the wheel with bounded stderr. Medium: a lone surrogate (any non-UTF-8 POSIX argument) crashed the CLI with a traceback. Low: missing stdout raised, missing stderr sent error lines to stdout, a `str` subclass lying about `__len__` or `__eq__` escaped the limits or changed results. Fixed in the next commit (`surrogateescape` output, guarded streams, plain-text reads, `tests/test_contract_three.py`) |
| c. Adversarial and robustness | 2 (new reviewer) | 7f2d93d | FAIL (1 medium) | 111 checks reproducing round 1 (97 fixed), 60,000 seeded in-process cases and 300 subprocess CLI runs on the wheel, 20,000 in-process CLI runs with real text streams, scaling linear to 320k. Medium: surrogates outside U+DC80 to U+DCFF (reachable from Windows argv) still crashed the CLI on output. Fixed in the next commit: refused in one line with status 1, contracts for U+D800, U+DBFF, U+DC00, U+DFFF |
| c. Adversarial and robustness | 3 (new reviewer) | 41781b6 | PASS (info) | every lone surrogate U+D800 to U+DFFF through every command on both platforms and as option values: 32,672 in-process runs with real text streams and 828 subprocess runs on the wheel, no traceback, single bounded stderr line, documented statuses. Info: on Windows a lone surrogate in U+DC80 to U+DCFF is written as its raw byte (the documented surrogateescape behaviour) |
| d. Packaging and real e2e | 1 | 46d9403 | PASS (2 low, 2 info) | on Elena's PC: build, `twine check --strict`, `check-wheel-contents`, archive contents as documented; the sdist suite with `src` removed against the wheel on 3.10.22 (356 passed, 5 skipped), 3.11.13, 3.12.15, 3.13.16, 3.14.2 and 3.14.8 free-threaded (357 passed, 4 skipped each; 3.11.17 blocked by that PC's launcher policy); outside consumer, console script and `python -m lvpath` by subprocess; PyPI 0.3.1 upgraded in place, 27 change-list claims confirmed, old pickles load; `check.ps1` and a no-upload copy of `release.ps1` behave as commented. Lows (scripts assumed the repo root as current folder, a dead `.gitignore` exclude) fixed in the next commit; info: the README's GUIDE link resolves only after the merge, a PyPI token exists on the build PC |
| e. Contract strength | 1 (blind) | 6c5ab4f | FAIL until its contracts were added | 40 mutations designed from the source alone, full suite with `-x` on this PC: 33 killed, 7 survivors, none equivalent (0xFFFF path type refused, a 40-character value marked as cut, default platform inverted, blank text taken as not-a-path, the mixed-slash UNC prefix refused, the `\\.\` device prefix dropped, the stderr cap loosened). Its seven proposed contracts added in `tests/test_contract_strength.py`; the seven mutants re-applied on the laptop are all killed by them |

## Independent reviewer (item 16)

| Review | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- |

## Decisions for the maintainer

- LabVIEW could not be driven on 2026-10-15 (NI sign-in server error), so no value was set
  and flattened through a running LabVIEW; the flattened form is checked against what
  LabVIEW 2026 itself saved into its install, against NI's example and against the type
  codes of LabVIEW's `cintools/extcode.h`. Type `2` is decoded as not-a-path
  (`NotAPathError`); type `3` (UNC) is named but refused, since no UNC record exists to
  confirm its component layout.
- Paths are ASCII only in the flattened form, as before; no record in the install holds a
  non-ASCII byte, so a code page was not guessed.
- The fixture keeps eleven short records copied byte for byte from NI files with their file
  and offset (path values only, as the 0.3.1 fixture does for text values).
- GUIDE.md and this report are longer than 200 lines; the limit applies to source files.
- The README links to GUIDE.md and CHANGELOG.md on `main`, so publish after the merge.

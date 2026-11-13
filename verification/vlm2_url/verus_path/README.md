# Verus: WHATWG URL path state vs rust-url 2.5.8
(authored by agents)

Nothing was filed upstream and no maintainer was contacted (human instruction). All findings are local.

## Result
- Verified (33 items, 0 errors): rust-url's segment-level path logic equals a hand-transcribed WHATWG path state for every input, except when the divergence predicate `bad` holds. Equality holds for all inputs on which `run_ok` holds (`run_ok` = `bad` never fires during the run).
- Six divergences were found, each machine-checked as a concrete Verus lemma. Five were also seen in the real crate, plus one spec deviation (CE5).

## Files
- `path_spec.rs`: spec, port, lemmas, counterexamples.
- `probe/src/main.rs`: differential test against the real `url = "=2.5.8"` crate.
- `probe/diff_test.rs.txt`: copy of that differential test.

## Spec (WHATWG, fetched 2026-11-03 from https://url.spec.whatwg.org/)
`s_shorten`, `s_step`, `s_run`, and `sp` (the path serializer). They transcribe path state step "c is EOF or / or (special and \)":
- double-dot: shorten, then append the empty string if there was no separator.
- single-dot: append the empty string if there was no separator.
- otherwise, for file with an empty path and a Windows drive letter, replace the second code point with `:`; then append the buffer.
- Shorten refuses only when the scheme is file, the path has size 1, and path[0] is a normalized drive letter.
- Dot matching is ASCII case-insensitive.

## Port (rust-url 2.5.8 src/parser.rs, `path_start` = 0)
Verus spec fns, not exec code.

| Verus fn | parser.rs lines |
|---|---|
| `i_step` (body of the outer loop of `parse_path`) | 1209-1366 |
| `i_run` (outer loop iteration) | 1209-1366 |
| `i_parse_path` (file post-pass) | 1372-1379 |
| `lsc` (`last_slash_can_be_removed`) | 1384-1393 |
| `i_shorten` | 1397-1410 |
| `i_pop` | 1413-1424 |
| `i_swdl` (`starts_with_windows_drive_letter`) | 1791 |
| `i_wdl` (`is_windows_drive_letter`) | 1777 |
| `i_nwdl` (`is_normalized_windows_drive_letter`) | 1770 |
| `i_pswdl` (`path_starts_with_windows_drive_letter`) | 1782 |

Also ported:
- The dot match arms (1319-1340): `i_ddot` has 9 literals, `i_dot` has 3.
- The file drive-letter replacement (1344-1363).
- The `_` arm fix-up that inserts `/` after a bare `/C:` (1289-1304), modelled at the start of `i_step`.

## Abstracted from the real code
- **Input splitting.** Segments are taken as already split on `/` (and `\` for special schemes) and as bytes; they contain no `/`.
- **Tab/newline stripping.** Modelled as already done. The `ascii_tab_or_new_line` branch (1263-1273) is not modelled. A probe with tabs (`file:///C:\tx`) gave `C:x`, as the spec says.
- **Percent-encoding.** Identity: no encode set is applied. `?` and `#` terminate the input before this function.
- **Other.** `has_host`, violation logging, and `Context::PathSegmentSetter` are dropped. `unwrap()` in `pop_path` (1415) is modelled as identity; the proof shows `rfind` is `Some` wherever it is used.
- **Pre-parse input.** `parse_path_start` (1150-1187) and `parse_file` (512+) are not ported. Entry states are `ser = sp(path)+"/"`, plus the two shapes in the next two lines.
- **Relative-file entry.** Parser.rs:658 is modelled as `shorten_path(sp(base))`, as in `rel_agree`.
- **Absolute-file entry.** A host-empty `file:///` entry (539-541) is modelled as an extra leading empty segment (CE6).

## Proved
- `step_lemma`: from the invariant `ser == sp(path)+"/"`, one step equals the spec step, unless `bad`; if `bad`, it differs. It also shows `i_assert_ok` (the debug_assert at 1321).
- `run_agree`: whole-run equality under `run_ok`.
- `parse_path_agree`: includes the file post-pass; see the CE5 deviation below.
- `rel_agree`: relative resolution at 658/810 for all non-bad bases. The `/C:` case is repaired by the fix-up.
- Other lemmas: `dots_eq` (spec dot matching = literal arms), `pswdl_iff`, `pop_sp`, `trim_lemma`, `wf_*`.
- Not proved: unbounded end-to-end divergence beyond the concrete runs below; the exec Rust code itself; the parse_path_start / host states; chars-level (tab) behaviour.

## Divergences (each a Verus lemma; CE1-CE4 and CE6 reproduced on the real crate)
`bad` = ".." applied after a segment `X:` or `X|` (alpha, then `:`/`|`, then end or `\`), where the spec would pop it. Cause: `last_slash_can_be_removed` (1384) uses the drive-letter test with no scheme check, and shorten/pop only compare `path[start..]`, which begins with `/` (so the check at 1403 is dead code).
- **CE1** (`ce1_nonfile_drive_dotdot`): `http://h/C:/../x` gives `http://h/C:/x`; spec gives `http://h/x`. Also for `foo://`. This is the rust-url #1130 class: the drive-letter rule applied to non-file schemes.
- **CE2** (`ce2_file_nonfirst_drive_dotdot`): `file:///a/C:/../x` gives `file:///a/C:/x`; spec gives `/a/x`. The spec refuses to pop only when the drive letter is the sole segment.
- **CE3** (`ce3_file_relative_base_ends_in_drive`): base `file:///a/C:` joined with `x` gives `file:///a/C:x`; spec gives `file:///a/x`. `pop_path` refuses to pop `C:` when it is not the first segment.
- **CE4** (`ce4_debug_assert_fails`): base `file:///a/C:` joined with `..` or `../x` hits the debug_assert at parser.rs:1321, which panics in debug builds. Release builds return `file:///a/C:` or `file:///a/C:/x`. This is a reachable panic via `Url::join`.
- **CE6** (`ce6_file_triple_slash_pipe_drive`): `file:///c|` stays `file:///c|`; spec and `file:/c|` give `file:///c:`. The root `/` is passed to `parse_path` as an empty first segment (539-541), so the "path is empty" test fails; the post-pass trim hides the extra slash. Also `file:///c|/a` and `file:///./c|`.
- **CE5** (`ce5_file_leading_empty_segments`, spec deviation, not a bug): `file:////a` gives `file:///a`. The current path state does not remove leading empty segments (old-spec behaviour kept at 1372-1379).

Differential test (`probe`): all strings of 1-5 segments from {a, C:, c|, .., ., %41, %2E%2e, C:\z, empty} under `http://h`, `file://` and `foo://h` (`\`-containing segments skipped for special schemes), 141325 inputs compared with a reference path state that includes the CE5 collapse. 40929 mismatches; 0 of them fall outside the predicted classes (`bad` or CE6). 2276 inputs where `bad` holds yield equal output (later steps mask the local divergence), so `bad` is a sufficient local condition, not an end-to-end one. Most mismatches by count are the same few classes.

## Re-run
```
cd /hdd1/sichangheagent/vl_meeting_work/out/vlm2_url/verus_path
timeout 600 /hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus path_spec.rs --multiple-errors 30
# expect: verification results:: 33 verified, 0 errors  (a GLIBC_2.39 warning line is harmless; z3 swapped per vlm_servo/SUMMARY.md)
cd probe && timeout 500 cargo run --release --offline -q   # needs url-2.5.8 in ~/.cargo registry
```
(`probe/src/main.rs` is the differential test; the single-URL probes were run by temporarily replacing it.)

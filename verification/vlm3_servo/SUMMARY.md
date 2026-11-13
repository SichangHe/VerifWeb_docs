# vlm3_servo: Verus on cssparser, Servo components/, smallbitvec heap
(authored by agents unless marked 🧑)

Takeaway: round 1's next steps are all done. Six agents produced proofs in all three areas, and smallbitvec is now fully proved, inline and heap halves together. The proof attempts and follow-ups found 4 likely-real bugs; 2 were confirmed by running the code and 2 by reading the source. Most proofs are on numeric or structural skeletons; floats and interior mutability were left out. Each agent's `REPORT.md` has the verbatim Verus failures, rerun commands, code changes and effort.

Setup: the same as round 1 (Verus 0.2026.11.02, z3 swapped; see `../vlm_servo/SUMMARY.md`). Servo is at commit `d275164b2bf624ee5844b22522d10c81b8f606ab` and cssparser at 0.38.0.

## Likely-real bugs (not filed upstream)
1. cssparser `is_ident_start`, `tokenizer.rs:931`: in the `-` then `\` case it calls `has_newline_at(1)`, which checks the backslash instead of the byte after it. So `-\<LF>` tokenizes as `Ident("-")`, where CSS Syntax 3 gives `Delim('-')`. The agent ran this on the crate, and I confirmed it in the source. It has not been compared with a reference tokenizer.
2. cssparser `current_line_number` (u32) overflows on input with more than 2^32 newlines (over 4 GiB). It panics with overflow checks on and wraps silently in release. The agent ran this on the crate.
3. Servo `components/shared/net/mime_classifier.rs`, `Mp4Matcher::matches`: when box_size is 12, the check on line 481 passes and `data[16..box_size]` on line 496 panics, for example on 12 bytes `00 00 00 0C 66 74 79 70 ...`. The agent ran the verbatim function body, and I confirmed it in the source. That network sniffing can reach it is an inference; Servo was not built.
4. Servo `script/dom/file/blob.rs:325`: in `Blob.slice` on an already-sliced blob, `parent_range.start + start` overflows i64, for example `b.slice(1).slice(1e19)`. Debug builds panic; in release, a standalone copy of the code returns the whole blob. The agent did not check which mozjs version Servo pins, and that decides the clamp behavior.

Edge cases at extreme sizes only (above about 18M px), which the agents judge benign:
- `content_rect` saturates and falls outside `padding_rect`; reachable via CSS like `width:1e9px`
- the float rule-7 check gives a false "fits" when `walls.inline_end == MAX_AU`
- table extra-width distribution has no rounding fix-up, so widths can be off by about 1 Au per column (source reading only)
- pixels:
  - the byte-length check returns `None` when width is huge and height is 0
  - the flip only asserts `len%4==0`
  - un-premultiplying silently truncates when c>a

## Per component
Each line gives the directory, then the Verus result ("N verified" counts proof obligations, all with 0 errors), then what was proved.

- `cssparser_tokenizer/`: `tok.rs` (19), `tok2.rs` (41). Proved:
  - the position, newline, hex and escape helpers
  - `consume_comment` finds the first `*/`
  - the quoted-string functions return correct stop positions
  - `consume_name`, when an identifier starts, always consumes at least one byte
  - `consume_numeric` stays in bounds and terminates; the i32 clamp is checked only on a u64 model

  Not proved or ported: decoded string contents, column tracking, url functions.
- `cssparser_misc/`: Proved:
  - `unicode_range` (18): no overflow, bounds ≤ 0x1000000
  - the serializers (`ser.rs` 9, `ser2.rs` 10): output matches per-byte escape specs, and `from_utf8_unchecked` only ever sees ASCII
  - `nth_full.rs` (11): An+B parsing cannot panic or overflow, given that the tokenizer produces b ≥ 0 (source reading)
  - `color.rs` (6): hex colors cannot overflow u8

  Blocked by floats: hsl/hwb conversion, `write_numeric`.
- `smallbitvec_heap/`: `sbv_full.rs` (96) is one SmallBitVec, inline and heap halves together, proved against a `Seq<bool>` model. Proved functions: `new`, `get`/`set`, `push`/`pop`, `reserve`, `reallocate` (including the inline-to-heap spill), `truncate`, `clear`, `clone`, and freeing. It uses vstd `PointsTo`/`allocate`/`deallocate` and one trusted `assume_specification` for `ptr::add`.

  Unsupported, so the code was rewritten around them: `usize as *mut T`, `Vec::from_raw_parts`, `mem::forget`, `mem::replace`, `slice::from_raw_parts_mut`, `Vec::as_ptr`. The proof assumes capacity bounds.
- `servo_fragment_tree/`: Proved:
  - `frag.rs` (17): rect and offset math, and `ContainingBlockManager`
  - `find.rs` (4): the recursive `find` over `Vec<Arc<Node>>` terminates, using a ghost fuel parameter
  - `sov.rs` (7): `scrollable_overflow_for_parent` stays in range and the result contains its inputs, given no saturation
  - `arc.rs`: read-only shared `Arc` children work in Verus

  Blocked: `ArcRefCell`/`AtomicRef`, atomics, `Cell` memoization, style-crate types, the transform branch.
- `servo_layout_algos/`: Proved:
  - `sizing.rs` (16): `ContentSizes` and `shrink_to_fit`
  - `flex_cross.rs` (14): align-content never divides by zero and leaves exactly 0 free space
  - `float_fits.rs` (9): the float fit check is sound, assuming non-negative object sizes
  - `table_flex_loops.rs` (12): the table width blend sums exactly to the target, and the flex-length resolution loop terminates
  - `float_tree.rs` (12): an AA-tree spec model keeps BST order and its unwraps cannot panic
  - `table_extra_width.rs` (5): the extra-width rules cover every case and their divisors are nonzero

  Not done: `LazySize` (OnceCell), AA balance, float arithmetic.
- `servo_misc/`: Proved:
  - pixels `p1`–`p3`: byte length, `multiply_u8_color`, flip index math, unmultiply, `get_rect`
  - `RelativePos` blob ranges
  - `ByteMatcher` index math
  - `RangeAny::intersect` equals set intersection
  - the UTF-16 length and offset loops cannot overflow u32
  - canvas/pipeline counters

  Not done: range-request functions, most canvas and webgl size math.

## Recurring friction
- arithmetic:
  - `usize` needs `global size_of usize == 8`
  - nonlinear arithmetic needs hand-written lemmas
  - shifts need `bit_vector` lemmas
  - const shift expressions had to become literals
- `&mut` postconditions need the new `final()` rule
- missing vstd specs: `is_ascii_digit`, `trailing_zeros`-family, several raw-pointer/`mem` functions
- floats are not modelled, so float code was abstracted or skipped
- interior mutability (atomics, `Cell`, `OnceCell`, `ArcRefCell`) is unsupported
- structural recursion over `Vec<Arc<T>>` needs a ghost fuel parameter

Effort: each agent took about 1.5–2.5 h of wall-clock time over 2–3 rounds, with about 7–25 verify runs per round. The per-report numbers are in each `REPORT.md`.

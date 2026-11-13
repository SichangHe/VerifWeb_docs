# servo_misc: components/pixels (lib.rs) Verus attempts
(authored by agents unless marked 🧑)

Upstream: https://github.com/servo/servo, shallow sparse clone in `src_upstream/`, commit `d275164b2bf624ee5844b22522d10c81b8f606ab`. Files: `components/pixels/lib.rs`. (`components/net/mime_classifier.rs` does not exist at this commit; net not attempted.)
Verus 0.2026.11.02. Rerun: `V=/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus; $V p1.rs; $V p2.rs; $V p3.rs` (each ends `0 errors`; p1: 9 verified, p2: 10, p3: 18).
Effort: about 25 verify runs, ~1 h wall clock; 170 lines total, roughly 55% spec/proof.

## Results (all three files: proved)

Fact: p1 `compute_rgba8_byte_length_if_within_limit`: `Some(v)` implies `v == 4*w*h <= 2^31-1`. `None` implies `4*w*h > 2^31-1 || 4*w > usize::MAX`.
Fact: p1 `multiply_u8_color` (verbatim body): no u32 overflow; `r == (a*b+127)/255` (checked with a `bit_vector` proof, as an unconditional fact over all u8 pairs); `r <= min(a,b)`; 255 is the identity.
Fact: p2 `flip_y_rgba8_image_inplace` index arithmetic (slice ops replaced by index checks): given `len == 4*w*h`, no underflow in `len - rl*hh`, and all `top`/`bottom` row ranges stay inside `left`/`right`.
Fact: p3 `unmultiply_inplace` per-channel: for premultiplied input (`c <= a`), `c*255/a <= 255`, so `as u8` is lossless.
Fact: p3 `rgba8_get_rect` borrowed fast path: `start + area*4 <= len` given the rect is inside the image and `len == 4*w*h`.

## Findings (not bugs in the strict sense; spec-level observations)

1. Postcondition surprise (p1, failed attempt 1). My first postcondition `None => 4*w*h > MAX` was rejected:
```
error: postcondition not satisfied
 8 | /         match r {
 9 | |             Some(v) => v == 4 * width * height && v <= 2147483647,
10 | |             None => 4 * width * height > 2147483647,
```
Reason (inference from the fix): for `height == 0` and `width > usize::MAX/4`, `checked_mul(4,width)` fails so the function returns `None`, although the true size is 0. This matches the doc ("None if overflow occurred") but not "size exceeds limit". Callers with `height == 0` and a huge width are rejected. Low impact.
2. `flip_y_rgba8_image_inplace` only asserts `len % 4 == 0`, not `len == 4*w*h`. File `p2_fail_a.rs` (log `p2_fail_a.log`) models the upstream precondition alone; Verus reports `possible arithmetic underflow/overflow` at `let cut = len - row_length * half_height;` (and the multiplications and the row-range assertion). So a slice shorter than `w*h*4` panics (Rust's checked arithmetic or slicing panic), not UB. The caller contract `len == 4*w*h` is required and proved sufficient in p2.
3. `unmultiply_inplace` has no validity check: `p3_fail_unchecked.rs` (log `p3_fail_unchecked.log`): `postcondition not satisfied` for `r == c*255/a` with a note `value may be out of range of the target type`, since the `as u8` truncates when `c > a` (e.g. c=255, a=1: 65025 as u8 = 1). Defined behavior, but wrong pixels for malformed (non-premultiplied) input. `multiply_u8_color` output satisfies `c <= a` (p1), so Servo's own premultiply output is safe.

## Code changes vs upstream
- `Option::checked_mul/and_then/filter` replaced by nested `match` (combinators with closures unsupported); `checked_mul` itself has a vstd spec (my own `external_fn_specification` was rejected as duplicate).
- Slice ops (`split_at_mut`, `swap_with_slice`, `chunks_mut`, `Cow`) not modeled: only the index arithmetic was ported (p2, p3 get_rect), so the proofs do not cover the byte contents of flip/get_rect results.
- `Size2D/Rect` replaced by raw `u32` fields; `global size_of usize == 8;` assumed (64-bit).
- `unmultiply` and `get_rect` ported per channel / index-only.

## Verus lessons and failures
- Spec-mode `>>` on `u32` expressions fails to typecheck (`no method named spec_shr found for struct int`); arithmetic in specs is `int`. Fix: cast `((cc + (cc >> 8u32)) as u32) >> 8u32` inside `by (bit_vector)`.
- Loops need `decreases` explicitly (`loop must have a decreases clause`).
- Nonlinear products (`i*rl`, `y*w*4`) needed manual `by (nonlinear_arith)` lemmas and manual commutation (`H*W == W*H`); the main cost of the session.
- Not done: net parsers, script UTF-16 index helpers, `copy_rgba8_image`, `clip`, byte-content correctness of flip.

# Round 2 additions (coordinator: broaden)

Locations at commit d275164 (found with grep; sparse checkout widened to `components/`):
- MIME sniffing: `components/shared/net/mime_classifier.rs` (not `components/net`); tests in `components/shared/net/tests/mime_classifier.rs`.
- Content-Range / Range: no Content-Range parser; range handling is `components/net/protocols/mod.rs:get_range_request_bounds`, `components/shared/net/filemanager_thread.rs:RelativePos`, `components/net/http_cache.rs:handle_range_request`, `components/shared/net/request.rs:validate_range_header`.
- UTF-16/UTF-8 offsets: `components/shared/base/text.rs` (`Utf16CodeUnits::*`, `RangeAny::intersect`). ID/epoch: `components/shared/base/id.rs`. Canvas size math: `components/canvas/vello_cpu_backend.rs:worker_thread_count` (only small piece looked at).
Rerun: `$V p4.rs; $V p5.rs; $V p6.rs; $V p7.rs`. Results: p4 5 verified, p5 1, p6 13, p7 5, all 0 errors.

## REAL BUG 1: `Mp4Matcher::matches` panics on short boxes (mime_classifier.rs:463-503)
Fact: for 12+ byte input whose box-size (bytes 0-3, big-endian) is a multiple of 4, <= len, and < 16, with `ftyp` at 4..8 and no `mp4` at 8..11, the code evaluates `data[16..box_size]` with start > end (or start > len) and panics. Verus (`p4_fail_mp4.rs`, index arithmetic only, slice = precondition `a <= b <= len`):
```
error: assertion failed
  --> p4.rs:15:12
   |
15 |     assert(16 <= box_size && box_size <= len);   // slicing precondition
   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
```
(log: `p4_fail_mp4.log`.) Verus gives no counterexample; I built one by hand and confirmed by compiling the verbatim function body (`poc/m.rs`, rustc -O): input `00 00 00 0C 66 74 79 70 61 62 63 64` (12 bytes) gives
`thread 'main' panicked at m.rs:33:17: range start index 16 out of range for slice of length 12`. Also box-size 0 with len >= 16 panics (`16..0`). Unit tests only cover box sizes >= 16. Fix verified in p4.rs (`mp4_fixed`): `if box_size < 16 { return false; }` (matches spec: bytes-read=16 is not < box-size, loop skipped, return false).
Inference (not run): `Mp4Matcher` is in `audio_video_classifier` (line 591), applied to network response bytes during sniffing, so remote content could trigger a panic in the net/fetch thread. I did not build Servo to confirm reachability or the thread's panic handling. Not filed upstream.

## REAL BUG 2: `Blob.slice` on a sliced blob overflows i64 (script/dom/file/blob.rs:325-328)
Code: `start: parent_range.start + start.unwrap_or_default()` and `end.map(|end| end + parent_range.start)`, with `slice(optional [Clamp] long long start, ...)`.
Fact: mozjs 0.15.7 `clamp_to` (conversions.rs:274-289) returns `D::MAX` for large inputs, so JS can pass `i64::MAX`. I used 0.15.7 from crates.io; whether Servo pins this version was not checked.
Fact: root Cargo.toml has no `overflow-checks` for release (only `checked-release` sets it).
Inference: `b.slice(1).slice(1e19)` computes `1 + i64::MAX`, which panics in dev builds and wraps to `i64::MIN` in release; `to_abs_range` then treats it as "from the end", clamps to 0, and returns the whole blob (my standalone replica `poc/blob.rs` prints `range = (0, 10)` for size 10), where the File API clamps start to size and returns an empty blob. Not run inside Servo. Same `+` pattern in `RelativePos::slice_inner` (filemanager_thread.rs:67).
Verus (`p7_fail_flatten.rs`): 
```
error: possible arithmetic underflow/overflow
  --> p7.rs:38:5
   |
38 |     parent_start + start
```
Fix verified (`flatten_start_fixed`): clamp-to-i64 add; result then flows through `to_abs_range`.

## Proved (p4-p7)
- `RelativePos::to_abs_range` (verbatim): given `size <= i64::MAX`, all arithmetic is overflow-free, `.to_usize().unwrap()` cannot fail, `start <= end <= size`, and start equals the spec'd clamp. `to_abs_blob_range` (`orig.end+1` cannot overflow; `start <= end <= size`). Caveat: `size as i64` for `size > i64::MAX` is not covered (precondition).
- `ByteMatcher::matches` index math: `len >= plen`, `start < len-plen+1` imply the whole pattern is compared and the returned `start+plen <= len`.
- `RangeAny::intersect` (p5): result bounds equal the set intersection (both soundness and completeness over all u32 x), `None` only when empty.
- p6: `Utf16CodeUnits::length_of`, `to_utf8_code_units_in_iter` (single string): for well-formed UTF-8 (my recursive `wf` spec: lead byte + n-1 continuation bytes), u32 accumulators never overflow for `len <= u32::MAX` and result <= len. Key lemma `prefix_bound`: every prefix sum of utf8/utf16 per-byte lengths <= total length (induction using `shift8/shift16/conts`). Without `wf` (invalid bytes) prefix sums can exceed len; `&str` guarantees wf, but I did not prove that `&str` implies my `wf` (assumed).
- `worker_thread_count` u16*u16 in u32 never overflows. `PipelineNamespace::next_index`: upstream `self.index += 1` is a plain add; model returns None at `u32::MAX`; the `expect("pipeline id index wrapped!")` then panics only after 2^32 ids (not a practical issue).

## Verus lessons (new)
- Slices are not modeled; encoding `a[x..y]` as an assertion `x <= y <= len` finds slicing panics but yields no counterexample.
- `saturating_add` has no vstd spec ("is not supported"); use explicit branches.
- Recursive spec fns on `Seq<u8>` with induction lemmas worked first try except two missing `prefix_bound` calls at loop exit/early return.
- Effort this round: ~15 verify runs, ~1.5 h; 120 lines code+spec per file average. Not done: canvas/webgl size math beyond one fn, `get_range_request_bounds`, `http_cache::handle_range_request`, `validate_range_header`, `to_utf32_code_units_in`.

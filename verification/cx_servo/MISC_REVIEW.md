# Independent review: Servo miscellaneous proofs
(authored by agents unless marked 🧑)

Reviewed `out/vlm3_servo/servo_misc/REPORT.md` and the matching `SUMMARY.md` claims. Source commit is `d275164b2bf624ee5844b22522d10c81b8f606ab` (`git rev-parse HEAD` confirmed). All execution used copies in `out/cx_servo/misc_work`. No Servo build or browser execution was performed.

## Findings requiring correction

1. **Overstated: the proposed blob fix is a complete fix.** Report: “Fix verified (`flatten_start_fixed`): clamp-to-i64 add; result then flows through `to_abs_range`.” The function proves saturating addition only, not nested Blob.slice semantics. `b.slice(2).slice(-1)` for a ten-byte original must select original bytes `[9,10)`; the proposed addition gives `2 + (-1) = 1`, then `[1,10)`. Independent executable `misc_work/blob_fix_case.rs` prints “saturating fix range = (1, 10); expected (9,10)”. Clamp each child offset against the sliced parent's length before composing absolute positions; separately preserve parent bounds. Saturating addition addresses the reported positive-overflow example, not the underlying composition problem.

2. **Overstated summary: “the UTF-16 length and offset loops cannot overflow u32”.** `p6.rs` requires `wf(bytes@), bytes.len() <= u32::MAX` and models one string, not the iterator of strings. Restore those qualifications. Upstream explicitly documents its `AssumeUnder4GB` marker: “trying to compute past `u32::MAX` code units may result in integer overflow.” Source: [text.rs](https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/shared/base/text.rs#L179-L184). The component report correctly states the assumptions.

3. **Overstated: “So a slice shorter than `w*h*4` panics” and “The caller contract `len == 4*w*h` is required”.** The equality is sufficient, not necessary: height 1 executes zero swaps regardless of buffer length, including an empty slice. Height 3 can also execute safely with only two rows. Replace with “some undersized slices panic; equality is sufficient.” The proof failure establishes the missing guarantee, not universal failure of short slices.

4. **Overstated source coverage for `rgba8_get_rect`.** The report's explicitly index-only theorem is valid, but it omits a relevant upstream arithmetic operation: source computes `rect.size.area()` and `size.area()` in `u32`, whereas p3 computes `(rw as usize) * (rh as usize)` in 64 bits. Thus the proof does not cover overflow in the source's area computations. Summary “get_rect” should say “borrowed-path index model, assuming exact dimensions and 64-bit arithmetic.” Source: [pixels/lib.rs](https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/pixels/lib.rs#L154-L168): “`assert_eq!(size.area() as usize, pixels.len() / 4);`” and “`let area = rect.size.area() as usize;`”.

## Claim-by-claim results

### Verification and provenance

**Confirmed:** “p1: 9 verified, p2: 10, p3: 18” and “p4 5 verified, p5 1, p6 13, p7 5, all 0 errors.” Reran all seven copied files using `tools/verus-x86-linux/verus`; the corresponding `misc_work/p*.rerun.log` contain those exact counts. The tool emits a weak `GLIBC_2.39` warning but exits zero on these successes. All four negative examples reproduce their documented diagnostic kinds: p2 arithmetic/range failures, p3 postcondition/truncation, p4 slice assertion, p7 addition overflow. Exact logs retained.

**Unverifiable historical claims:** “about 25 verify runs, ~1 h wall clock”, “~15 verify runs, ~1.5 h”, “roughly 55% spec/proof”, unsuccessful first attempts not preserved, and claims about which changes were difficult or worked first try. Current files cannot establish session history. **Confirmed:** the report's “170 lines total”: p1–p3 total exactly 170 physical lines. Missing/unsupported-feature statements describe that session, not independently established universal Verus limitations; the working replacements are visible.

**Confirmed source locations:** shared/net MIME and filemanager files, shared/base text and ID files, pixels lib, script Blob implementation, and canvas vello CPU backend exist in the recorded tree. The opening “net not attempted” is superseded by round 2. Broad negative “no Content-Range parser” was not independently established by exhaustive source audit; classify **unverifiable**. “Not done” claims are consistent with the delivered proof files, but historical effort outside them is unverifiable.

### Pixels p1–p3

**Confirmed:** p1 byte-length postconditions, exact `(a*b+127)/255`, bounds by both operands, identity at 255, and safe arithmetic. The executable multiply body matches upstream. `None` at huge width and zero height follows directly from the first checked multiplication. Source documentation says: “Computes image byte length, returning None if overflow occurred or the total length exceeds the maximum image allocation size.” [pixels/lib.rs](https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/pixels/lib.rs#L57-L69). “Low impact” is an unvalidated judgment, not a proof result.

**Confirmed, conditional:** p2's row-index arithmetic with `len == 4*w*h`, and p3's per-channel nontruncation with `c <= a`. The actual slice operations, byte-content effects, and malformed short pixel chunks are outside these models. p3's borrowed-rectangle bound holds under its explicit positive rectangle dimensions and exact length assumption, subject to finding 4 above.

**Confirmed:** malformed nonpremultiplied channel `255`, alpha `1` computes 65025 and truncates to 1. p1 establishes that premultiply's output meets `c <= a`. Whether malformed pixels occur in Servo callers was not demonstrated. The summary's placement of these pixel observations under “extreme sizes only (above about 18M px)” is **wrong** for missing flip length validation and malformed premultiplied channels: neither requires large images.

**Confirmed modeling disclosures:** raw dimensions replace geometry types; p2/p3 assume 64-bit usize; slice mutation, Cow, and actual pixel contents are absent. p1 does not itself declare the global 64-bit assumption. The `get_rect` copy path is not proved beyond common preliminary arithmetic.

### MP4 bug and p4

**Confirmed:** short-box panic condition and 12-byte reproducer. Compiled the copied body with `rustc -O`; it panics: “range start index 16 out of range for slice of length 12”. Independent cases with 16-byte buffers and box sizes 0, 4, 8, 12 all panic; box size 16 returns false; all return true when the major-brand bytes are `mp4`, as required by the short-circuit condition. Evidence: `misc_work/mp4_cases.rs` and `.log`. Copied body matches [upstream matcher](https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/shared/net/mime_classifier.rs#L461-L503).

**Confirmed, narrowly:** p4 proves the added `box_size < 16` guard makes the modeled slice bounds safe, provided it is placed after the existing early major-brand success. It does not prove the full fixed matcher: its final value is unconditionally false and it omits the compatible-brand scan. The guard is consistent with the [MIME Sniffing Standard](https://mimesniff.spec.whatwg.org/#matches-the-signature-for-mp4): “Let bytes-read be 16.”; “While bytes-read is less than box-size, continuously loop through these steps:”; “Return false.” Retrieved standard text is saved in `misc_work/mimesniff.txt`.

**Confirmed source inclusion, unverified runtime reachability:** matcher is in `audio_video_classifier`, and the classifier invokes it. No full browser/network execution or panic-handling audit was done, so retain the report's explicit inference qualification. The focused unit tests inspected include a file fixture and a 260-byte box; the claim that every fixture's box size is >=16 is **unverifiable** without inspecting all referenced binary fixtures.

**Confirmed, narrow:** ByteMatcher arithmetic proves sufficient data remains for `plen` bytes and `start+plen <= len`. “the whole pattern is compared” also needs the actual mask to have matching length, because upstream zips data, pattern, and mask. Upstream validation checks this; p4 has no mask model. No matching-content correctness is proved.

**Confirmed:** u16 canvas dimension product fits u32. **Overstated summary:** “canvas/pipeline counters” suggests upstream counter verification; the pipeline model replaces overflowing addition with an Option return. Source says “`self.index += 1;`” then “`NonZeroU32::new(self.index).expect("pipeline id index wrapped!")`” ([id.rs](https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/shared/base/id.rs#L234-L236)). Overflow panics directly with checks or wraps to zero and then panics without checks; the model proves its replacement behavior. “Not a practical issue” is an unvalidated judgment.

### Blob overflow and p7

**Confirmed source arithmetic and standalone outcomes:** [blob.rs](https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/script/dom/file/blob.rs#L323-L328) contains “`start: parent_range.start + start.unwrap_or_default(),`” and “`end: end.map(|end| end + parent_range.start).or(parent_range.end),`”. `RelativePos::slice_inner` independently contains plain additions. Reran copied blob repro in debug and optimized builds; wrapped start is -9223372036854775808 and range `(0, 10)`; the checked plain addition panics. The first portion of that reproducer explicitly uses `wrapping_add`, so it demonstrates modeled release arithmetic rather than executing Blob::Slice itself.

**Resolved dependency uncertainty:** report used mozjs 0.15.7 and said the pin was unchecked. Actual commit's Cargo.toml says “`js = { package = "mozjs", version = "=0.26.14", default-features = false, features = ["intl", "libz-sys"] }`”; Cargo.lock agrees. [Manifest](https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/Cargo.toml#L146). Downloaded the pinned crate from https://crates.io/api/v1/crates/mozjs/0.26.14/download without building it. Its `src/conversions.rs:249–250` says “`if d >= D::MAX.cast() {`” followed by “`return D::MAX;`”. [Versioned source](https://docs.rs/crate/mozjs/0.26.14/source/src/conversions.rs). The IDL says “`Blob slice(optional [Clamp] long long start,`” ([Blob.webidl](https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/script_bindings/webidls/Blob.webidl#L17)). Thus the stated conversion behavior also holds in the pinned version. Generated binding execution remains untested.

**Confirmed profile statement:** root manifest only explicitly enables overflow checks under `checked-release`; regular release has no such setting. External build flags could override this, so debug/release outcomes are conditional on normal compiler settings.

**Confirmed expected empty result:** [File API slice algorithm](https://w3c.github.io/FileAPI/#slice-blob) says “Otherwise, let relativeStart be min( start , originalSize ) .” and “Let span be max(( relativeEnd - relativeStart ), 0) .” For a nine-byte sliced blob and huge positive child start, span is zero. Saved specification text: `misc_work/fileapi.txt`. Actual Servo UI/API behavior remains **unverifiable by this review's execution**, as no browser was built.

**Confirmed conditional p7 proofs:** with `size <= i64::MAX`, `to_abs_range` proves arithmetic safety, bounded ordered output, and the stated start clamp; cast models replace `to_usize().unwrap()`. The proof does not specify exact end semantics. `to_abs_blob_range` proves its bounded endpoints and no overflow of `orig.end+1` on the assumed 64-bit target. Saturating-add theorem passes, with semantic limitation in finding 1.

### Range intersection and UTF-16 p5–p6

**Confirmed:** p5 proves membership equivalence over all u32 points, and None implies no member. It does not establish Some implies a nonempty set: an unbounded-start, end=0 range can return Some with zero u32 members. Report's precise “None only when empty” is valid; don't strengthen it to an equivalence.

**Confirmed conditional p6 results:** helper equations, prefix bounds, safe accumulation, returned offsets <= input length, and length equals modeled per-byte sum. The assumed UTF-8 shape is weaker than Unicode validity but valid UTF-8 satisfies its byte-shape constraints; that implication is not formally proved here, as the report admits. No semantic postcondition says the returned offset identifies the requested character boundary; the proof only bounds it. Invalid byte sequences can break the bound. Multi-string iteration is omitted. Restore these limits in any broad summary.

## Evidence boundaries

Proofs establish properties of the copied Verus models, not equivalence to all upstream behavior. No upstream report was filed and no maintainer was contacted. The most useful improvements to the reviewed reports are to separate upstream code, proof model, and candidate fix; state preconditions beside summary claims; and avoid treating verification of saturating addition as verification of Blob.slice.

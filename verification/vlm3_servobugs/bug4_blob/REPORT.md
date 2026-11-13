# Servo Blob.slice overflow (bug4) - verdict: PARTIALLY CONFIRMED (claimed repro is wrong; a different repro works)
(authored by agents unless marked 🧑)

Commit d275164b2bf624ee5844b22522d10c81b8f606ab (local checkout verified: HEAD matches; checkout is sparse, so Cargo.toml/Cargo.lock/codegen fetched from raw.githubusercontent at that commit into raw/).
Same code is still on servo main (checked 2026-11-03).

## 1. The claimed repro `b.slice(1).slice(1e19)` does NOT overflow
IDL (components/script_bindings/webidls/Blob.webidl, https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/script_bindings/webidls/Blob.webidl#L16-L18):
    Blob slice(optional [Clamp] long long start, optional [Clamp] long long end, optional DOMString contentType);
Codegen passes the Clamp flag (codegen.py:849 `isClamp = type.hasClamp()`, :1156 `getConversionConfigForType(type, isEnforceRange, isClamp, ...)`).
Pinned mozjs (Cargo.toml:146): `js = { package = "mozjs", version = "=0.26.14", ... }` (Cargo.lock: mozjs 0.26.14).
mozjs 0.26.14 src/conversions.rs:
    impl_num!(i64, 0, -(1 << 53) + 1, (1 << 53) - 1);          // line 130
    ConversionBehavior::Clamp => Ok(ConversionResult::Success(clamp_to(unsafe { ToNumber(cx, value) }?)))
    if d >= D::MAX.cast() { return D::MAX; }  if d <= D::MIN.cast() { return D::MIN; }
So 1e19 -> 2^53-1 = 9007199254740991 (clamped to the WebIDL "lower/upper bound" of long long, NOT i64::MAX, not modulo). Single step: 1 + (2^53-1) = 2^53, no overflow. The agent's concern about mozjs version was the right question; answer: 0.26.14 clamps to +-(2^53-1).

## 2. But the overflow is real via chaining (~1025 slices)
Slice on a Sliced blob (blob.rs:322-329, https://github.com/servo/servo/blob/d275164b2bf624ee5844b22522d10c81b8f606ab/components/script/dom/file/blob.rs#L322-L329):
    BlobData::Sliced(grandparent, parent_range) => {
        let range = RelativePos {
            start: parent_range.start + start.unwrap_or_default(),
            end: end.map(|end| end + parent_range.start).or(parent_range.end),
        };
Result is stored against the grandparent, so starts accumulate unclamped. Each slice(1e19) adds 2^53-1; i64 overflows at the 1024th add (2^63/2^53 = 1024). JS: `let s=b.slice(1); for(let i=0;i<1100;i++) s=s.slice(1e19);` (also `end` path: `end + parent_range.start`; also negative direction with -1e19). Also RelativePos::slice_inner (components/shared/net/filemanager_thread.rs:67-76) has the same unchecked adds.
Repro: repro/main.rs (verbatim copies of mozjs clamp_to specialised to i64 with the real MIN/MAX, RelativePos, the Sliced branch). Not a Servo build (too heavy; mozjs-sys needs SpiderMonkey); the real JS->i64 conversion is mozjs's clamp_to, copied. Results:
- single `b.slice(1).slice(1e19)`: start=9007199254740992, abs range 10..10 on a 10-byte blob (correct, empty).
- chain, debug (overflow-checks on): panics "attempt to add with overflow" at i=1024.
- chain, rustc -O (checks off): wraps; start becomes -9214364837600035840 (negative), to_abs_range(10) = 0..10, i.e. whole blob instead of the correct empty blob. Silent wrong data.

## 3. Spec
https://w3c.github.io/FileAPI/#slice-method-algo (raw/spec_slice.txt): "If start is negative, let relativeStart be max((originalSize + start), 0). Otherwise, let relativeStart be min(start, originalSize)." Same for end; "Let span be max((relativeEnd - relativeStart), 0)". Correct result for the chain is an empty blob (clamped to size each step). Servo defers clamping to the end (to_abs_range) and adds unclamped offsets in between, so intermediate overflow is possible.
Other engines: not checkable (no browser here). Node v22.21.1 (not a browser) gave size 9 for `b.slice(1).slice(1e19)` on a 10-byte blob (spec says 0), suggesting Node wraps 1e19 mod 2^64; irrelevant to Servo.

## 4. Reachability / consequence
Reachable from any web page JS (Blob.slice is exposed, no flags); needs ~1025 calls, trivial.
Cargo.toml has no [profile.release] section and no overflow-checks override: dev profile = overflow checks ON (Rust default); release / production / profiling (debug-assertions=false) = OFF (Rust default, wraps). Only `checked-release` (Cargo.toml:424-427) and dev enable them. So:
- dev/checked-release: panic in script thread (inferred: whole content process / script thread aborts; Servo panics in script thread are typically fatal to that pipeline) - DoS of own page only.
- release/production: silent wrap; wrong slice (whole blob / wrong range) - correctness issue, not memory-unsafe (to_abs_range clamps to [0,size] before to_usize().unwrap()). In the wrapped-negative case start<0 gives max(size+start,0); I did not find a path to a panicking unwrap in release (not exhaustively tested; end wrapping not tested).
Severity: low.

## 5. Upstream
`gh search issues/prs --repo servo/servo` for "Blob slice overflow", "blob.rs slice parent_range", etc. returned no relevant issue/PR. Not filed (per instruction).

## 6. Side observation (read from code, not run)
Sliced branch adds parent_range.start to a negative `start`/`end`, but negative values are relative to the parent's size, not the grandparent's: e.g. 10-byte b, `b.slice(2,8).slice(-1)` -> start=1, end=Some(8) => bytes 1..8 instead of 7..8. Likely separate correctness bug; unverified by execution.

## Verdict
Original claim as stated (single `slice(1e19)`): NOT reproducible (clamp to 2^53-1). Underlying defect (unchecked i64 add on accumulated ranges): CONFIRMED with chained slices; debug panic, release wrong result.

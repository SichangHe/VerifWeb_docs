# Independent review of Boa's `at()` fix
(authored by agents unless marked 🧑)

The guard change is correct under the stated length bound. No correctness defect found in the two changed match arms. Before merging, add permanent regression tests. The proof establishes index selection for a model, not complete JavaScript method correctness.

## Prioritized findings

1. **Medium: the patch omits regression tests.** [at_fix.patch](../vlm6_atfix/at_fix.patch) changes only the guards and one comment. The draft says, “I can contribute a test262 or Boa regression test.” Include Boa tests with the fix: finite indices at and below `-2**63` for both methods, an array containing the erroneous negative property, and the valid `-length` boundary. The existing external repro is useful evidence but does not run with Boa's normal tests.
2. **Low: separate the crashing repros.** In [the draft](../vlm4_drafts/boa_at_overflow.md), the first repro is `console.log(String("abc".at(-1e300)));`. It aborts the process, so the subsequent string and array examples never execute. Present three independent CLI invocations, or explicitly say to run each example separately. The array-only reproduction is [array_repro.js](array_repro.js).
3. **Low: disclose the proof's architecture assumption.** The draft says, “assuming `0 <= len <= 2^53 - 1` and the saturating conversion above.” [at_proof.rs](../vlm6_atfix/at_proof.rs) also states `global size_of usize == 8;`. Add “on a 64-bit target” to the proof sentence. This matters to the String model's cast to `usize`; it is not evidence that the patch fails on 32-bit targets.

The report appropriately labels the original debug panic as untested and the proof as a port. Keep both qualifications. The decimal literal `-9223372036854775807` rounds to `-2**63` as a JavaScript Number; use `-(2 ** 63)` or explain the rounding to avoid suggesting an exact integer test.

## Independent proof run and assumptions

Commands from the workspace root:

```sh
tools/verus-x86-linux/verus out/vlm6_atfix/at_proof.rs
tools/verus-x86-linux/verus --cfg 'feature="orig"' out/vlm6_atfix/at_proof.rs
```

[Fixed log](verus_fixed.log): `verification results:: 4 verified, 0 errors`. [Original log](verus_orig.log): `verification results:: 4 verified, 2 errors`, with `error: possible arithmetic underflow/overflow` at both negations. The original configuration includes the fixed functions as well. Z3 reports `Z3 version 4.16.0 - 64 bit`; the existing solver replacement was sufficient. Both invocations printed a weak `GLIBC_2.39` diagnostic, but verification ran to completion.

Trusted boundaries:

- `requires 0 <= len <= MAX_SAFE, boa_models(ri, s)` assumes the length bound and correspondence between the runtime integer and the mathematical input. Saturation equivalence is proved *given* that correspondence. Floating-point conversion, `ToNumber`, coercion side effects and exceptions are outside the proof.
- Array's length bound has a direct source justification: [to_length](boa/core/engine/src/value/mod.rs) uses `.clamp_finite(0, Number::MAX_SAFE_INTEGER as i64)`. [length_of_array_like](boa/core/engine/src/object/operations.rs) calls it for generic objects; real arrays use a `u32` length. String uses `let len = s.len() as i64;`; the proof assumes the ECMA String bound rather than verifying every constructor or the cast. No whole-engine string-size invariant was proved in this review.
- `global size_of usize == 8;` restricts the String model to 64-bit targets. Actual 32-bit strings have a tighter size constraint, but this file does not prove that case.
- The models return an index or `None`; they do not verify property access, getters, substring construction, object representation or memory safety. Source correspondence between the copied arms and Boa is manually checked.
- The original Array model substitutes `-i` for `i.abs()` under `i < 0`. This catches the same signed-minimum overflow; it does not formally verify Rust's `abs` implementation or release wrapping behavior. The runtime repro supplies separate evidence.
- No `assume`, admitted proof, or external-body function appears in this proof file. Verus, vstd, Z3 and the translation itself remain trusted.

For a negative integer, `i >= -len` is equivalent to `len + i >= 0`. Together with `i < 0`, it gives `0 <= len + i < len`; the bound on `len` makes negation and addition safe. Saturated huge inputs remain out of range because `len` is far smaller than either signed-64-bit endpoint.

## ECMA-262 correspondence

Fetched the TC39 primary source on 2026-11-04; retained [spec.html](ecma262.html). The following quotes preserve the source's algorithm notation, with HTML entities rendered.

[ToAbsoluteIndex](https://tc39.es/ecma262/#sec-toabsoluteindex):

```text
1. Let _int_ be ? ToIntegerOrInfinity(_value_).
1. If _int_ is finite and _int_ < 0, set _int_ to _length_ + _int_.
1. Return _int_.
```

[String.prototype.at](https://tc39.es/ecma262/#sec-string.prototype.at):

```text
1. Let _thisValue_ be the *this* value.
1. Perform ? RequireObjectCoercible(_thisValue_).
1. Let _string_ be ? ToString(_thisValue_).
1. Let _length_ be the length of _string_.
1. Let _k_ be ? ToAbsoluteIndex(_index_, _length_).
1. If _k_ < 0 or _k_ ≥ _length_, return *undefined*.
1. Return the substring of _string_ from _k_ to _k_ + 1.
```

[Array.prototype.at](https://tc39.es/ecma262/#sec-array.prototype.at):

```text
1. Let _obj_ be ? ToObject(*this* value).
1. Let _length_ be ? LengthOfArrayLike(_obj_).
1. Let _k_ be ? ToAbsoluteIndex(_index_, _length_).
1. If _k_ < 0 or _k_ ≥ _length_, return *undefined*.
1. Return ? Get(_obj_, ! ToString(𝔽(_k_))).
```

[String type](https://tc39.es/ecma262/#sec-ecmascript-language-types-string-type), verbatim HTML: `The <dfn variants="is a String,is not a String">String type</dfn> is the set of all ordered sequences of zero or more 16-bit unsigned integer values (“elements”) up to a maximum length of 2<sup>53</sup> - 1 elements.` [ToLength](https://tc39.es/ecma262/#sec-tolength) specifies: `1. Let _clampedLength_ be the result of clamping _length_ between 0 and 2<sup>53</sup> - 1.`

The proof's `spec_at` matches the index selection in these algorithms. Its `None` for both infinities is justified because either infinity fails the range check. For `-1e300` and length 3, the mathematical index remains negative and the required result is `undefined`, with no property read.

## Build and runtime evidence

Fetched Boa upstream `main` into an isolated checkout at [boa/](boa/): `329e89748ed34e218fe593b4209b1dbe1d6eb64d`, unchanged from the supplied patch base. Applied the original patch without modification. Built independently with `cargo build --release -p boa_cli -p boa_tester -j 4`; [build.log](build.log) ends with `Finished \`release\` profile [optimized] target(s) in 5m 17s`. Available memory was 144 GiB immediately before the build, above the required 60 GiB.

Used test262 checkout `831359a4192ef83b8c50f91363d2ff739fe550f6` and the checked-in Boa `test262_config.toml`. From `out/cx_atfix/boa`, ran:

```sh
target/release/boa_tester run --test262-path ../../vfy_at/src/test262 --suite test/built-ins/String
target/release/boa_tester run --test262-path ../../vfy_at/src/test262 --suite test/built-ins/Array
target/release/boa ../../vlm6_atfix/repro.js
target/release/boa ../boundaries.js
target/release/boa ../array_repro.js
```

- [String log](test262_String.log): `Passed tests: 1221`, `Ignored tests: 2`, `Failed tests: 0 (0 panics)`.
- [Array log](test262_Array.log): `Passed tests: 3083`, `Ignored tests: 0`, `Failed tests: 0 (0 panics)`.
- [Supplied repro rerun](repro_fixed.log): all ten cases print `ok`; the two large-negative string cases and poisoned-array case return `undefined`.
- [Additional boundary checks](boundaries.log): `boundary checks passed`. [Script](boundaries.js) checks empty receivers, negative and positive saturation, infinities, NaN, signed zero, `-length`, maximum array-like length, and a Proxy that must observe only the length read for an invalid index.
- [Array-only fixed result](array_fixed.log): `undefined`.
- Existing unfixed binary from `out/vfy_at/src/boa/target/release/boa`, rerun independently: [string log](baseline_string.log) contains `Message:  Unexpected get()`; [array log](baseline_array.log) contains `42`. This baseline binary was reused, not rebuilt.

All fixed build and runtime commands exited successfully. The standalone supplied repro only prints failures; I also inspected all ten results. No debug build or full `cargo test` run was performed. These are release results with the runner's existing exclusions, not a claim of full-suite conformance.

## Workflow feedback

Keep a runnable build/test command beside result summaries, including the test262 checkout path and runner configuration. This packet supplied logs but required rediscovering those arguments. Record the 64-bit assumption alongside the length and conversion assumptions. No input files were edited and nothing was posted upstream.

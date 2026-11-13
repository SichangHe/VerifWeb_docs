# cx_hunt2: builtin edge-case hunt in Nova, plus uncovered Boa builtins
(authored by agents unless marked 🧑)

## Result
Nova main has 6 confirmed bugs and 1 minor accuracy issue. Boa main has 1 bug with no matching issue or test262 test in my searches, and 2 earlier Boa findings got wider. I re-ran every repro on the current main of each engine before writing this. Nothing was filed or posted upstream.

What "confirmed" means here:
- each bug has a JS repro in `repro/`, and the outputs are saved in `repro/runs.txt`
- each expected value comes from ECMA-262. I fetched it at 7628258 as `../cx_builtins/spec.html`
- V8 (node 22.21.1) was only a cross-check. Node 22 predates some features (Iterator helpers limit, base64), so where it disagrees with the current spec I used the spec.

Versions:
- Nova main `877ef1629c47dc4ea495335912975b271d0e3b82`. I built `nova_cli` in release mode at `tgt/release/nova_cli`. Nova has no `console`, so the Nova repros use `print`.
- Boa main `329e89748ed34e218fe593b4209b1dbe1d6eb64d`. This is still HEAD according to the GitHub API. I used the existing binary `../poke_esmeta/work/boa_bin/bin/boa` and a fresh source clone in `boa/`.
- test262 `d1154377`, cloned to `t262/`.

How I checked whether a bug is already known:
- issues: `gh search issues` on trynova/nova and boa-dev/boa; every query and its results are saved in `search-issues.txt`
- test262 coverage: grepped specific `t262/` directories, not the whole tree; the commands and results are saved in `search-test262.txt`
- Nova's own known test262 failures: `nova/tests/expectations.json`. Below, "listed as FAIL" means a test262 test exercises the bug and Nova already records that test as failing.

## Nova: confirmed bugs
1. Integer conversion goes through a saturating cast instead of wrapping modulo 2^32.
   - Affects ToInt32, ToUint32, ToInt16, ToUint16, ToInt8 and ToUint8.
   - Cause: `trunc() as i64 as i32` (and the same for u32/i16/u16/i8/u8). Rust's `as i64` saturates. See `type_conversion.rs:694,733,769,805,841,877`.
   - Not every |x| ≥ 2^63 gives a wrong result. Wrong results are shown only for the positive inputs in the repro; the independent evaluation found `(-(2**64))|0` correctly returns 0.
   - Reach is wider than in Boa, where Int32 conversion was correct. Here it also breaks the `|`, `>>>` and `<<` operators, typed-array stores, `Math.clz32`, `Math.imul` and `String.fromCharCode`.
   - Repro: `(2**64)|0` gives -1 and `(1e20)>>>0` gives 4294967295. The spec says 0 and 1661992960. File: `repro/n1_toint32.js`.
   - test262: a grep for literals of 2^63 or more in the bitwise and shift expression directories, `Math/clz32`, `Math/imul`, `String/fromCharCode` and `TypedArrayConstructors` matched only two unrelated BigInt tests (`search-test262.txt`). This is not a search of the whole tree.
   - Issues: no matching Nova issue found in the searches listed in `search-issues.txt`.
2. `Number.prototype.toString(radix)` uses exponent notation for large and small numbers when the radix is not 10.
   - Example: `(2**53).toString(16)` returns `"2.0ed"`; the spec says `"20000000000000"`. In base 16 and above, `e` is itself a digit, so the output reads as a different number.
   - Spec quote (Number::toString): "If _radix_ ≠ 10 or _n_ is in the inclusive interval from -5 to 21, then" it returns plain digits; scientific notation comes only after "Assert: _radix_ is 10."
   - Cause: `lexical` is called with `JAVASCRIPT_LITERAL` float options. See `types/language/number.rs:1328,1336`.
   - The test262 radix tests use only small values and pass in Nova. No matching Nova issue found in the searches listed in `search-issues.txt`. File: `repro/n2_radix.js`.
3. RegExp `lastIndex` silently loses any value that is not a u32 integer.
   - Example values: `1.5`, `"2"`, `2**32`. Reading `lastIndex` back gives `undefined`, and `exec` treats it as 0. So `/a/g` with `lastIndex = 2**32` matches `"aaa"`; the spec says null.
   - Cause: in `builtins/regexp.rs:344`, the guard is `if !new_last_index.is_valid() && value.is_undefined()`. It looks inverted: a non-u32 value is never written to the backing object.
   - Known in tests, not in issues: test262 covers it (e.g. `RegExp/prototype/exec/S15.10.6.2_A4_T8.js` uses `lastIndex = "12"`), and those tests are listed as FAIL. No Nova issue names the cause. File: `repro/n3_lastindex.js`.
4. `Number.prototype.toExponential` is wrong in two ways.
   - First: `toExponential(0)` behaves like `toExponential()`, so `(25).toExponential(0)` returns `"2.5e+1"`; the spec says `"3e+1"`. Cause: `if f == 0` sends it to the shortest-output path, at `number_prototype.rs:114`.
   - Second: ties round to even, so `(1.25).toExponential(1)` returns `"1.2e+0"`; the spec says `"1.3e+0"` (spec: "pick the _e_ and _n_ for which _n_ × 10^(_e_ - _f_) is larger"). Cause: Rust `format!("{x:.f$e}")`. Boa has the same bug as open issue boa-dev/boa#4169.
   - Known in tests, not in issues: `toExponential/return-values.js` is listed as FAIL. No matching Nova issue found in the searches listed in `search-issues.txt`. File: `repro/n4_toexponential.js`.
5. `Number.prototype.toPrecision` is wrong for every |x| below about 1e-100, not only subnormals.
   - Examples: `(1e-101).toPrecision(1)` returns `"0e+101"`. `(9e-101).toPrecision(1)` returns `"1e-100"`, which is wrong but looks plausible.
   - Cause: `format!("{x_f64:.100}")` at `number_prototype.rs:273`. This code was ported from Boa (`builtins/number/mod.rs:493`), and Boa gives identical output.
   - Known in tests, not in issues: test262 `staging/sm/Number/toPrecision-values.js` covers it and is listed as FAIL. No matching Nova issue found in the searches listed in `search-issues.txt`. File: `repro/n5_toprecision.js`.
6. `%TypedArray%.prototype.copyWithin` panics when argument coercion shrinks the buffer below `startIndex` or `targetIndex`.
   - Repro: a length-tracking `Uint8Array` over a resizable buffer, with `copyWithin({valueOf(){b.resize(3);return 0}}, 4)`. Nova panics with "range end index 7 out of range for slice of length 3". The spec and node do no copy.
   - Cause: `new_len - start_index` underflows (usize) at `typed_array_intrinsic_object.rs:790`.
   - test262 `copyWithin/coerced-target-start-end-shrink.js` only shrinks to lengths larger than the indices, so it misses this case (checked only in that file). No matching Nova issue found in the searches listed in `search-issues.txt`. File: `repro/n6_copywithin.js`.

## Nova: minor
- `Math.hypot(1e300,1e300)` returns `Infinity`, and `Math.hypot(1e-300,1e-300)` returns 0; V8 gives about 1.41e±300.
  - The spec calls hypot "implementation-approximated", and its warning about overflow is a non-normative note. So this is a quality issue, not a spec violation. I did not look for the cause. File: `repro/n7_hypot.js`.
- `"a".padEnd(2**53-1)` and `String.raw` with a huge `raw.length` abort the whole process ("memory allocation of 9007199254740991 bytes failed").
  - JS code cannot catch an abort; Boa throws a RangeError here instead.
  - This is not a spec violation, since the spec sets no string length limit.

## Boa: new results (builtins not covered by vlm6)
1. `Uint8Array.prototype.setFromBase64` panics when an options getter shrinks the target's buffer.
   - Boa panics at `array_buffer/utils.rs:288` with "index out of bounds".
   - Cause: `builtin_uint8.rs:146` reads the array length before the options getters run at line 161. The spec reads the options first, then runs "Let _taRecord_ be ? ValidateTypedArrayBounds(_into_, ~seq-cst~)" on the current length.
   - test262: `setFromBase64/detached-buffer.js` covers a getter that detaches the buffer; a grep for `resize` in that directory found nothing (`search-test262.txt`). No matching Boa issue found in the searches listed in `search-issues.txt`. File: `repro/b1_setfrombase64.js`.
   - `setFromHex` takes no options, so it cannot hit this.
2. Wider than vlm6 found: `Atomics.add` panics at the same place as `Atomics.store` (`array_buffer/mod.rs:116`). This is the same bug, now confirmed for a second operation. File: `repro/b2_atomics_add.js`.
   - The spec requires a RangeError for this repro. AtomicReadModifyWrite says "Perform ? RevalidateAtomicAccess(_ta_, _byteIndexInBuffer_).", and RevalidateAtomicAccess says "If _elementLastByteIndex_ ≥ _taRecord_.[[CachedBufferByteLength]], throw a *RangeError* exception." Here those values are 3 and 0. V8 throws TypeError instead.
   - test262: in `built-ins/Atomics`, only two `notify` tests mention `resize`. The `add` and `store` tests that use `valueOf` cover type validation and immutable buffers, not shrinking (`search-test262.txt`).
   - Issues: Boa searches for "Atomics", "Atomics panic" and "Atomics resize" returned no matching issue (`search-issues.txt`).
3. Wider than vlm6 found: the toPrecision bug (vlm6 bug 5) is already open as boa-dev/boa#5225.
   - The issue says "for subnormal floats". In fact every |x| below about 1e-100 is affected, including normal numbers such as `2.2250738585072014e-308`. Some inputs also give a plausible but wrong answer: `(9e-101).toPrecision(1)` returns `"1e-100"`.
4. Wider than vlm6 found: the narrow-integer saturation bug (vlm6 bug 1) also reaches `String.fromCharCode(2**64)`, which returns code unit 65535 instead of 0.

## Checked, no bug
- Boa behaves correctly on:
  - Iterator `take` and `drop` throw RangeError for a limit above 2^53-1. The current spec requires this ("If _numberLimit_ is finite and _numberLimit_ > 𝔽(2^53 - 1)"); node 22 is older and accepts it.
  - Float16Array, `Math.f16round` and `DataView.getFloat16` rounding.
  - `Math.sumPrecise`.
  - TypedArray `copyWithin` when the buffer shrinks.
  - JSON `space` clamping and Date limits.
  - array-like objects with a `length` of 2^53 or more.
- Nova matched the spec on: `at`/`with`/`slice`/`fill`/`splice` relative indices, ArrayBuffer `slice`/`resize`, the Atomics and DataView resize cases, String methods, Date, BigInt `asIntN`/`asUintN`, `Array` length limits, and JSON.
- Not tested in Nova because it lacks the feature: Iterator helpers (calling them throws TypeError, so they appear unimplemented), `ArrayBuffer.prototype.transfer` ("not implemented"), base64, Float16Array.
- Not tested: Intl, Temporal.

## Takeaways
- Nova shares Boa's bug classes, and two of its bugs come from code shared with Boa.
  - The saturating `as i64` cast causes Nova bug 1, as in Boa.
  - Nova's toPrecision was ported from Boa, so Nova bug 5 and Boa #5225 are the same bug.
  - Grepping for `as i64 as` found all six conversion sites at once.
- The pattern "user callback resizes the buffer, then the engine uses a stale length" again caused the panics: Nova `copyWithin`, Boa `setFromBase64` and Boa Atomics. test262 tests detaching far more than shrinking, so these gaps are systematic.
- Nova's `expectations.json` already lists the test262 tests for its RegExp, toExponential and toPrecision bugs as failing. This shows the failures are recorded, not that the maintainers know the causes. For bugs 1, 2 and 6, neither the listed issue searches nor the listed test262 greps found anything matching. That does not prove they are new: keyword searches cannot establish novelty.

## Files
- `repro/*.js`: one repro per finding; `repro/runs.txt` holds their outputs
- `cases.txt`, `c2.txt`–`c7.txt`: all probe cases (tab-separated: name, expression)
- `run.py`: differential runner. Usage: `python3 run.py CASES [label "cmd args"]`
- `run1.txt`, `boa_run.txt`, `c6_*.txt`, `c7_*.txt`: probe outputs
- `nova/`, `boa/`, `t262/`: shallow clones; `tgt/`: Nova build output (`build.log`)

## Workflow feedback
- The packet mentioned a z3/Verus spec-driven method, but differential probing plus grepping for `as i64` found every bug faster. I wrote no proofs.
- `run.py` lacked a per-case timeout at first, so one 2^32-element `Array.from` case stalled the whole batch. Any reusable probe harness should have one.
- A full test262 run of Nova was not needed, because Nova ships an expected-failures list (`expectations.json`). Checking that list first separated recorded test262 failures from unrecorded ones.

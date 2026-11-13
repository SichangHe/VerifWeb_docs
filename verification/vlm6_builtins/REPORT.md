# vlm6_builtins: integer edge-case bug hunt in Boa builtins
(authored by agents unless marked 🧑)

## Result
Five new bugs reproduce on the real Boa CLI built from main 329e897. I re-ran every repro myself before writing this.

Caveat on method: the task asked for Verus or z3 specs. Only one z3 check was written, for `Array.prototype.at` (`A/at_guard.smt2`, sat). Everything else was found by reading the code and running differential probes against node, with the spec as tie-breaker. That covered about 50 builtins in four groups: A Array, B String, C TypedArray/ArrayBuffer/DataView/Atomics, D Number/Date/misc. Nothing was filed upstream.

## Confirmed bugs (new)
1. **Narrow integer conversion saturates instead of wrapping.**
   - Affects ToInt8, ToUint8, ToInt16 and ToUint16 for values ≥ 2^63. Int32 and Uint32 conversion is correct.
   - Cause: an `as i64` cast saturates, at `core/engine/src/value/mod.rs:1141-1290`.
   - Repro: `a=new Int8Array(1); a[0]=2**63; a[0]` returns -1; the spec says 0. `new Uint16Array([1e300])[0]` returns 65535; the spec says 0.
   - Reach: element stores, `fill`, `of`, `from`, DataView setters and `Atomics.store`.
   - Coverage: no test262 test uses values this large (grep for `2**64` and `1e300`), and no matching Boa issue was found.
   - Files: `C/r4.js`, `D/repro1.js`.
2. **`Array.prototype.at` returns a wrong value for indices ≤ -2^63.**
   - This is the same root cause as the known `String.prototype.at` crash, in a different builtin. The guard `i.abs() <= len` at `core/engine/src/builtins/array/mod.rs:756` wraps for `i64::MIN`.
   - Repro: `a=[1,2]; a["-9223372036854775806"]="BUG"; a.at(-1e300)` returns "BUG"; the spec says undefined.
   - z3: `A/at_guard.smt2` is sat with `i = i64::MIN`.
   - Coverage: test262 coverage for `Array.prototype.at` was assumed rather than checked. Its tests are believed to use only small indices, like the `String.prototype.at` tests. Boa issues were not searched.
   - File: `A/at.js`.
3. **`ArrayBuffer.prototype.slice` panics when argument conversion shrinks the buffer.**
   - Repro: `b=new ArrayBuffer(8,{maxByteLength:16}); b.slice({valueOf(){b.resize(2);return 0}},8)`
   - Boa panics at `array_buffer/mod.rs:741` with "range end index 8 out of range for slice of length 2". Node returns an 8-byte buffer.
   - File: `C/r1.js`.
4. **`Atomics.store` panics when index conversion shrinks the buffer.**
   - Repro: `Atomics.store(new Int32Array(b),{valueOf(){b.resize(0);return 0}},1)`, where `b` is a resizable 8-byte buffer.
   - Boa panics at `array_buffer/mod.rs:116`. Node throws a TypeError.
   - Only `store` was tested. Other Atomics operations probably share the code path.
   - File: `C/r2.js`.
5. **`(5e-324).toPrecision(p)` returns garbage.**
   - `toPrecision(1)` returns `0e+101`; the spec says `5e-324`.
   - No matching Boa issue was found. Other subnormal numbers were not tested.
   - File: `D/repro3.js`.

## Already known
- `toExponential` rounds ties to even, e.g. `(2.5).toExponential(0)` returns `2e+0` instead of `3e+0`. This is open as boa-dev/boa#4169.
- `String.prototype.at(-1e300)` crashes (found earlier, in `poke_esmeta`).

## No bug found
- String group: about 48.7k calls across 15 methods matched node.
- Array group: `slice`, `splice`, `fill`, `copyWithin`, `indexOf`/`lastIndexOf`/`includes`, `with`, `toSpliced` and the length limits (2^53-1, 2^32-1).
- Remaining TypedArray index, length and offset handling.
- `Number` `toString(radix)`, ToInt32/ToUint32, the `split` limit, RegExp `lastIndex`, Date, and `flat` depth.
- Another Rust JS engine was not attempted.

## Takeaways
- The main bug class is unbounded spec math replaced by saturating `as i64` casts. It produced bugs 1 and 2 and the `String.prototype.at` crash. Grepping for `as i64` and `.abs()` next to conversion code finds these faster than writing proofs.
- A second class is user callbacks that resize a buffer during argument conversion (bugs 3 and 4). These are outside the pure-integer Verus model; differential tests found them.

Details are in `A/`, `B/`, `C/`, `D/` (each has a RESULT.md); the shared brief is `BRIEF.md`.

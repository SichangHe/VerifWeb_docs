# Group A: Array.prototype index/length builtins (Boa 329e897, release CLI)
(authored by agents)

## Takeaway
One confirmed bug: `Array.prototype.at` with an index that ToIntegerOrInfinity saturates to i64::MIN reads a bogus negative-numbered property instead of returning `undefined`. All other tested builtins matched the spec.

## Confirmed bug: Array.prototype.at, i64::MIN
Code: core/engine/src/builtins/array/mod.rs:756 `Integer(i) if i < 0 && i.abs() <= len => len + i`.
`i = i64::MIN` (from any argument <= -2^63, e.g. -1e300): `i.abs()` wraps to i64::MIN (debug build: panic), so the guard passes and `k = len + i` is negative; `obj.get(k)` then looks up the string key of that negative number.
Spec: k = len + relativeIndex < 0 => return undefined.
z3 (`at_guard.smt2`): sat, i.e. guard holds with k < 0 (e.g. i = 0x8000000000000000).
Repro (`at.js`):
    var o={length:2,"-9223372036854775806":"BUG",0:"a",1:"b"};
    Array.prototype.at.call(o,-1e300)   // Boa: "BUG"   expected: undefined
    var a=[1,2]; a["-9223372036854775806"]="BUG"; a.at(-1e300) // Boa: "BUG"
Also with -(2**63), -1e19. Key is String(len + i64::MIN). Without the planted property Boa returns undefined (correct by accident), so only observable with that key; debug builds panic. Same root cause as the known String.prototype.at crash, different builtin.
test262: built-ins/Array/prototype/at tests use small indices only (not checked line by line). Boa issues: not searched (no network need; not filed).

## Checked, no bug (JS probes on Boa; files t.js, t2.js, sat.js, results*.txt)
Each compared by hand against ECMA-262:
- at, indexOf, lastIndexOf, includes: lengths up to 2^53-1 via array-likes, fromIndex of +-Infinity, +-1e300, +-2^63, -M, 2^53, -0, fractions.
- slice, splice, fill, copyWithin: start/end/deleteCount saturated and huge; len 2^53-1; overlap direction near the end; splice len+items > 2^53-1 gives TypeError; ArraySpeciesCreate count > 2^32-1 gives RangeError; species null/number/frozen result.
- with, toSpliced: index +-Inf/1e300 RangeError; newLen > 2^53-1 TypeError; len >= 2^32 RangeError; property read order.
- Array(len), length assignment (2^32-1 ok, 2^32/NaN/1.5/-1 RangeError, valueOf called twice, non-writable, non-configurable element), push/unshift at 2^32-1 and 2^53-1.
- Cosmetic only: `with` out-of-range message says "TypedArray operation".
- Not completed: loops over >=2^32 elements (with/flat/shift/concat on length ~2^53) hang, as the spec's loops do.
No Verus proof written; the i64::MIN hazard was found by reading the code and confirmed with z3 + the JS repro.

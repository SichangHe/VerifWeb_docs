# Group D result (method: differential run of Boa 329e897 release CLI vs node, plus manual spec check; no Verus/z3 proofs written -> all findings are "confirmed by repro", none proof-only)
(authored by agents unless marked 🧑)
Probe scripts: t.js u.js r.js x.js v.js; repros: repro1.js repro2.js repro3.js

## Confirmed bugs
1. ToInt8/ToUint8/ToInt16/ToUint16 wrong for |x| >= 2^63. Source: core/engine/src/value/mod.rs:1141-1290 does `number.abs().floor().copysign(number) as i64`; Rust `as i64` saturates, so the value becomes i64::MAX then `% 256`. Affects typed-array element stores (Int8/Uint8/Int16/Uint16Array), DataView.set{Int8,Uint8,Int16,Uint16}, Atomics.store, fill, of/from. Int32/Uint32 are fine.
   Repro (repro1.js): `a=new Int8Array(1);a[0]=2**63;a[0]` -> Boa -1, expected 0. `Uint16Array` with 1e21 -> 65535, expected 0. 2**63-1024 is still right. Also `2**64+2**13` into Int16Array -> -1, expected 8192.
   test262: no test hits values >= 2^63 in TypedArrayConstructors/internals/Set (grep found none). Boa issues: none found ("Int8Array overflow", "ToInt8").
2. Number.prototype.toExponential rounds ties to even instead of up (spec: "If there are two such sets of e and n, pick the e and n for which n x 10^(e-f) is larger").
   Repro (repro2.js): (2.5).toExponential(0) Boa "2e+0", expected "3e+0"; (25).toExponential(0) "2e+1" vs "3e+1"; (1.25).toExponential(1) "1.2e+0" vs "1.3e+0". toFixed/toPrecision are correct.
   Related issue: boa-dev/boa#4169 (OPEN) "Fix Number.prototype.toExponential() value rounding" -- known.
3. (5e-324).toPrecision(p) broken: Boa "0e+101" (p=1), "0.0000e+101" (p=5); expected "5e-324", "4.9407e-324". Only checked for MIN_VALUE; likely other subnormals. No issue found.

## Checked, no diff vs node (spec-consistent)
- toFixed/toPrecision/toExponential range errors, NaN/undefined digits, 1e21, -0; toString(radix) for radix 2..36, fractions, huge/tiny values; radix coercion (2.9, undefined, null).
- Math.clz32/imul, |0 >>> << ToInt32/ToUint32 incl. 1e300, 2^53+2, 2^64+2^12.
- String.prototype.split and RegExp [Symbol.split] limit (2^32+1, 2^32, -1, NaN, objects); limit-vs-separator coercion order.
- RegExp lastIndex (-Infinity, NaN, 2^53, 1e300, strings, objects) in exec/test/replace/match/matchAll/search/split, global/sticky/non-global; read-only lastIndex.
- Date: UTC, ctor, TimeClip boundaries, all setters with 1e300/2^53/Infinity, NaN dates, ISO parse limits, toISOString extremes. Date setter coercion order (setHours/setSeconds with mutating valueOf) matches the spec; node differs there, Boa is right.
- Array.prototype.flat depth (Infinity, -1, NaN, 2^32, 2^53, strings, null).

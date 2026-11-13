# vfy_at: independent check of the Boa String.prototype.at claim
(authored by agents unless marked 🧑)

## verdict
- claim confirmed: `"abc".at(-1e300)` panics Boa; spec answer is `undefined`
- claim confirmed: test262 has no test reaching it
- new finding: Array.prototype.at has the same overflow; it does not panic but returns a wrong value

## versions tested (release builds, built here)
- boa main 329e89748ed34e218fe593b4209b1dbe1d6eb64d (2026-10-31)
- boa tag v0.22 (latest release tag)
- test262 main 831359a4192ef83b8c50f91363d2ff739fe550f6 (2026-11-04)
- ecma262 main spec.html (fetched 2026-11-04)
- repro scripts: /tmp/vfy_at.js (one-liner `console.log(String(EXPR))`), /tmp/vfy_at2.js

## spec text (ecma262 main spec.html, verbatim)
String.prototype.at:
```
1. Let _thisValue_ be the *this* value.
1. Perform ? RequireObjectCoercible(_thisValue_).
1. Let _string_ be ? ToString(_thisValue_).
1. Let _length_ be the length of _string_.
1. Let _k_ be ? ToAbsoluteIndex(_index_, _length_).
1. If _k_ < 0 or _k_ ≥ _length_, return *undefined*.
1. Return the substring of _string_ from _k_ to _k_ + 1.
```
Array.prototype.at: same, with `1. Return ? Get(_obj_, ! ToString(𝔽(_k_))).`
ToAbsoluteIndex:
```
1. Let _int_ be ? ToIntegerOrInfinity(_value_).
1. If _int_ is finite and _int_ < 0, set _int_ to _length_ + _int_.
1. Return _int_.
```
So for -1e300, k = 3 + (-1e300) < 0 → undefined.
Note: current spec uses ToAbsoluteIndex; Boa's comments cite the older inline steps. Semantics are the same.

## boa source (identical at main and v0.22)
- ToIntegerOrInfinity saturates to i64::MIN for -1e300 (Rust `as` cast)
  https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/value/integer.rs#L61
  `let integer = number.abs().floor().copysign(number) as i64;`
- String.prototype.at
  https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/string/mod.rs#L541
  `IntegerOrInfinity::Integer(i) if i < 0 && (-i) <= len => (len + i) as usize,`
  - release: -i64::MIN wraps to i64::MIN, guard passes, `as usize` gives huge k, `get_expect` panics
- Array.prototype.at
  https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/builtins/array/mod.rs#L756
  `IntegerOrInfinity::Integer(i) if i < 0 && i.abs() <= len => len + i,`
  - release: i64::MIN.abs() wraps to i64::MIN, guard passes, k = len + i64::MIN (negative), then `obj.get(k)`
- TypedArray.prototype.at (typed_array/builtin.rs ~L385-392): computes `len + i` then checks `k < 0 || k >= len` → correct

## observed (same on main and v0.22)
- `"abc".at(-1e300)` → panic `Message: Unexpected get()  Location: core/string/src/lib.rs:466`
- `"abc".at(-9223372036854775807)` → same panic
- `"abc".at(-1e18)`, `"abc".at(-Infinity)` → undefined (correct)
- `var a=[1,2,3]; a["-9223372036854775805"]=42; a.at(-1e300)` → 42; spec → undefined (wrong)
  - plain `[1,2,3].at(-1e300)` → undefined only because the bogus key is absent
- correct results for -1e300 on: TypedArray at, String charAt/charCodeAt/codePointAt/substring/slice, Array slice/indexOf/with (RangeError, as spec requires; message wrongly says "TypedArray")
- debug build not tested (the original report says `-i` panics there; plausible by Rust overflow checks, unverified)

## test262 coverage
- test/built-ins/String/prototype/at/*: indices only in -4..4 plus non-numeric coercions
- test/built-ins/Array/prototype/at/*: indices only in -6..6
- test/staging/sm/{String,Array,TypedArray}/at.js: adds ±Infinity and NaN, which Boa routes through the non-Integer branch → not reached
- conclusion: no test passes a finite index ≤ -2^63 (or any large finite negative) to at

## existing Boa reports
- `gh search issues/prs --repo boa-dev/boa` for "String.prototype.at", "Unexpected get", "at panic", "at overflow": only #1596 (closed, "Implement Array.prototype.at()"); no report of this bug found

## nothing filed upstream

# poke_esmeta: ECMA-262 builtins → Verus specs → Boa proofs
(authored by agents unless marked 🧑)

## Result
I proved two Boa builtins against Verus specs transcribed from the ECMA-262 algorithm steps. The proof of the second one found a real crash in Boa, and I reproduced it on the real engine.

- `Array.prototype.indexOf`: proved. A port of Boa's `index_of` (`core/engine/src/builtins/array/mod.rs:1444`) matches the spec, including Boa's saturating `f64 as i64` conversion of fromIndex.
- `String.prototype.at`: Verus reports `possible arithmetic underflow/overflow` on `(-i) <= len` (`core/engine/src/builtins/string/mod.rs:541`). After a one-token fix (`i >= -len`), the port proves.
- Real-engine check: I built `boa_cli` from git HEAD 329e897. `"abc".at(-1e300)` and `"abc".at(-9223372036854775807)` crash Boa with `Message: Unexpected get()  Location: core/string/src/lib.rs:466`. The spec answer is `undefined`.
  - Cause: ToIntegerOrInfinity gives Boa `i64::MIN` (saturated). In a release build, `-i64::MIN` wraps back to `i64::MIN`, so the guard passes and `k` comes out huge. In a debug build, `-i` panics instead.
  - test262 gap: the 11 `String/prototype/at` tests use only indices in -4..4, so they never reach this case. `indexOf` tests do cover `-Infinity`, but Boa handles that through the separate NegativeInfinity branch.
- Nothing was filed upstream.

## What the specs cover
- Spec source: `spec.html` at the ecma262 commit ESMeta pins (0248456c), transcribed by hand into Verus `spec fn`s. ESMeta's own IR was not used; see the blockers below.
- Model assumptions:
  - Objects are lists of slots (absent, or present with a value).
  - HasProperty and Get are pure and don't throw, so there are no proxies or getters.
  - IsStrictlyEqual is modeled as `==`, which ignores NaN and -0.
  - ToIntegerOrInfinity is an input to the spec. ToObject, ToString and RequireObjectCoercible are not modeled.
- The ports are hand ports, not Boa's own source. Running Verus on Boa directly would mean modeling `Context`, `JsValue` and the GC.

## Blockers
- ESMeta does not build here. `sbt assembly` fails with `UnsupportedClassVersionError ... class file version 61.0 ... only recognizes class file versions up to 55.0`: ESMeta needs Java 17 and the host has Java 11. With Java 17, it might be possible to generate specs from ESMeta's IR mechanically instead of transcribing them by hand.

## Worth pursuing?
I think yes, at small cost. It took about 1 hour and found one real bug.
- Where it pays off: places where an engine replaces spec math (unbounded integers) with machine integers, i.e. overflow and saturation edge cases. Verus checks these exhaustively, while test262 samples only a few values.
- The expensive part is an object/property model with side effects (proxies, getters). That would be needed before going beyond these simple pure index functions.
- Cheaper next step: grep Boa for other `to_integer_or_infinity` + `-i`/`len + i` patterns (e.g. `Array.prototype.at`, `slice`, `TypedArray.at`) and prove or test each one.

## Files (work/)
- `builtins.rs`: specs and ports. `verus builtins.rs` → 7 verified, 0 errors. `verus builtins.rs --cfg 'feature="verbatim"'` → the overflow error.
- `repro.rs`: standalone demo of the guard bug. `t262/`: the test262 tests. `boa_bin/bin/boa`: the built CLI.

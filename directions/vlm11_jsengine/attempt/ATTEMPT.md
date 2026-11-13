# Verifying Boa's ToInt32 (`f64_to_int32`) in Verus
(authored by agents unless marked 🧑)

## Result
Verified: `f64_to_int32_bits(d64: u64) -> i32` returns exactly ECMA-262 ToInt32 of the double with bit pattern `d64`, for all 2^64 bit patterns (NaN, infinities, denormals, +-0 included). `verus toint32.rs --crate-type=lib` -> "40 verified, 0 errors". No `external_body`, `assume`, `admit`, or axioms in the file (grep-checked). Trusted base: Verus/vstd/Z3 only, plus the items under "Gaps".

Files (all in this directory): `toint32.rs` (proof), `mut1_sign.rs`, `mut2_exp32.rs`, `mut3_mask.rs` (mutants), `probe_false.rs` (assert(false) probe), `sanity.rs` (spec checked on concrete doubles).

## Prior work checked first
No earlier proof covers ToInt32/ToUint32 (grep over out/ found none). `out/vfy_at` and `out/cx_builtins` are bug hunts on `at`/`slice` index clamping, run, not proofs. `out/cx_proofs/REVIEW.md` finds earlier proofs often had `external_body` stubs (e.g. `unimplemented!()` bodies) or specs weaker than claims (mutants such as "always 0" passed). I designed against both: no trusted bodies, and mutants below.

## Spec (quoted from ECMA-262 ToInt32, written without bit tricks)
1. Let number be ? ToNumber(argument).
2. If number is not finite or number is either +0 or -0, return +0.
3. Let int be truncate(R(number)).
4. Let int32bit be int modulo 2^32.
5. If int32bit >= 2^31, return F(int32bit - 2^32). Otherwise return F(int32bit).

Spec in Verus (`s_*` functions): decode the IEEE-754 binary64 pattern with plain arithmetic (`/ 2^52 % 2048`, `% 2^52`, `/ 2^63`), value = +-m*2^e, truncate toward zero (multiply or integer divide), euclidean mod 2^32, recentre. Upstream uses shifts and masks; the spec does not.

## Mutants and probes (all must fail; they do)
- `mut1_sign.rs`: negative numbers keep positive sign -> "postcondition not satisfied", 39 verified, 1 error.
- `mut2_exp32.rs`: `exponent > 31` changed to `> 32` -> "precondition not satisfied" (shift overflow bound), 1 error.
- `mut3_mask.rs`: mask 0xFFFF_FFFF -> 0x7FFF_FFFF -> failures, 1 error.
- `probe_false.rs`: `assert(false)` after calling the function -> fails (1 error), so the contract is not contradictory.
- `sanity.rs`: the spec itself evaluated on 1.0 ->1, -1.5 ->-1, 2^31 ->-2^31, 2^32 ->0, 4294967295.0 ->-1, NaN, -inf, -0, min denormal ->0: 47 verified, 0 errors. This guards against a spec that is wrong but consistent with the code.

## Changes from upstream (conversions.rs, non-aarch64 `f64_to_int32`)
1. **f64 replaced by `u64` bits (blocker).** Verus has no usable f64 semantics: no `to_bits`, no `is_finite`, no f64 comparison/`as i32` casts with meaning. Upstream already works on `number.to_bits()`, so the helpers take the bits as argument instead. Trusted gap: that `f64::to_bits` is the IEEE bit pattern, and that the caller passes `x.to_bits()`. Not verified.
2. **Fast path deleted** (`if number.is_finite() && number <= i32::MAX && number >= i32::MIN { let i = number as i32; if f64::from(i) == number { return i } }`), 5 lines: it needs f64 comparisons and casts. It is a pure shortcut; the proof shows the slow path alone is already correct for all inputs, so the omitted lines can only matter if they are themselves wrong (not verified: that is the one upstream piece not covered).
3. Nested helper `fn`s hoisted to module level (Verus does not support nested fns); `number` -> `d64`.
4. Shift amounts cast to `u64` (`>> (-exponent) as u64`, `<< (exponent as u64)`) for Verus's shift typing.
5. `let bits = if ... {..}` became `let bits: u64; if ... { bits = ..}` so facts survive the join (Verus-specific; same semantics).
6. The final `as i32` and `as i64` casts annotated `#[verifier::truncate]`.
Everything else (constants, early returns, the `sign * bits as i64 as i32` combine) is verbatim.
Not covered: aarch64 `__jcvt` variant (intrinsic), `f64_to_uint32` (one-line `as u32` cast of this function; trivially follows but not proved), and callers.

## Effort
- Wall clock: 09:37:42 to 09:43:17 PST, 2026-11-07 (about 5.6 min by `date`; the harness clock, includes tool latency, one agent, no subagents).
- Verifier runs: about 30 (counted from the transcript, ~12 to get the main proof, ~3 mutants, 1 probe, ~12 to get the concrete sanity cases through Z3; the sanity file was the most fiddly part). The final proof run took about 1 s.
- Upstream LOC covered: ~73 lines (lines 6-78, incl. the 5-line fast path I dropped, so ~68 verified).
- Spec + proof LOC: 224-line `toint32.rs` total: spec 21, upstream-derived exec code ~70, proof/lemmas ~130; plus sanity ~40. So proof:code is roughly 2:1 for a 68-line function.
- Hard parts: connecting bit ops to arithmetic (`bit_vector` lemmas), u64 shift overflow (`x << e` truncates; proved via `(x & mask) << e`), i64->i32 cast wraparound (`lemma_cast`), and Z3 failing to evaluate `pow2` on literals (needed manual asserts).

## How many such components does the engine have?
Rough, from grep (`fn to_*`, `f64_to_*` in engine/src, tests excluded): about 43 numeric/index conversion functions in Boa's engine crate (ToInt32/Uint32/Int16/..., ToIntegerOrInfinity, ToLength, ToIndex, relative-index clamping, string-to-number, number-to-string, etc.). Whole Boa tree is ~234k Rust lines. This is a count of candidates, not verified components; the f64-heavy ones (number-to-string via dtoa, string-to-number parsing producing f64) hit the same f64 blocker and need an IEEE model.

## Assessment (opinion)
One small, self-contained, bit-twiddling function was verified fully in minutes by an agent, with an independent spec, mutants and no trust. That is evidence the leaf-function tier is doable. It is weak evidence for a whole engine: this function was chosen because it is pure and loop-free; the engine's bulk (object model, GC, interpreter, async) has aliasing, mutation and callbacks, and f64 arithmetic itself has no Verus support. A cost estimate per 70-line pure function is minutes to an hour of agent time, not extrapolable to the other 230k lines.

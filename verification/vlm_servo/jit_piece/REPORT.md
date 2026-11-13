# jit_piece: cranelift-bitset ScalarBitSet (u64)
(authored by agents unless marked 🧑)

Component: `cranelift-bitset` 0.125.0 (crates.io tarball, `src_upstream/cranelift-bitset-0.125.0/src/scalar.rs`).
Result: proved (contains, insert, remove, from_range) with one precondition upstream does not state; found a real edge-case bug.

## Properties (all proved, `bitset.rs`)
- model: element i in set iff bit i of the u64 is 1 (`inset`)
- `contains(i)` returns exactly `inset(self, i)`, no overflow of `1<<i` (i<64)
- `insert(i)`: returns "newly inserted"; result set = old + {i}
- `remove(i)`: returns "was present"; result set = old - {i}
- `from_range(lo,hi)`: result set = {j | lo <= j < hi}; no arithmetic overflow/underflow in `(one<<(hi-1)) + ((one<<(hi-1))-one)`, `(one<<lo)-one`, `hi_rng-lo_rng`

## Finding (fact, tested with rustc)
Upstream `from_range` asserts only `lo <= hi` and `hi <= capacity`. `from_range(64, 64)` (empty range) on u64 evaluates `1u64 << 64`.
- debug build: panics "attempt to shift left with overflow"
- `-O` build: shift amount is masked to 0, result is `0xffffffffffffffff` (full set, should be empty)
- Verus reports it as an overflow on `(one << lo) - one` when `lo < 64` is not assumed (see v1 below)
- my fix is a precondition `lo < 64`; upstream would need `lo < capacity` or special-casing

## Changes to the code
- generic `T` + trait `ScalarBitSetStorage` replaced by `u64` (Verus cannot reason about trait-generic shifts/bit ops)
- `assert!`s turned into `requires` (`i < 64`, `lo<=hi`, `hi<=64`) plus `lo < 64` (the finding above)
- `T::from(1)` -> `1u64`; `capacity()` hard-coded to 64
- not ported: `min`/`max`/`pop_*`/`len`/iterators (need `trailing_zeros`/`leading_zeros`/`count_ones`; not attempted), `CompoundBitSet`
- `mut self` postconditions need `final(self)` in this Verus version

## Failures (verbatim, trimmed)
1. `!has(...)` in a spec: `error[E0425]: cannot find function `hasnt` in this scope`. `has` is a Verus operator keyword, so `!has` lexed as `hasnt`. Told nothing useful about the cause; renamed spec fn to `inset`.
2. `error: to dereference a mutable reference parameter in a postcondition, disambiguate by wrapping it in either `old` or `final``. Clear; used `final(self)`.
3. v1 (`bitset_v1_fail.rs`, from_range with no proof):
   ```
   error: possible arithmetic underflow/overflow
     57 |  (one << (hi - 1)) + ((one << (hi - 1)) - one)
   error: possible arithmetic underflow/overflow
     59 |  let lo_rng = (one << lo) - one;
   error: possible arithmetic underflow/overflow
     60 |  ScalarBitSet(hi_rng - lo_rng)
   ```
   Pointed to the right 3 ops but not why; led to adding `lo < 64` and facts about the shifts.
4. `pow2`-based lemma: `cannot find function pow2` (needs import), then abandoned: bridging `int` spec arithmetic to u64 wrapping bit-vector arithmetic was awkward (`if` branches `int` vs `u64` type errors, `spec_shr` not on `int`).
   Fix: state the value as `0xffff...ffff >> (64-hi)` and prove it equal to the exec expression in a `by(bit_vector)` assert; then one `by(bit_vector)` assert gives the per-bit result.
5. "could not automatically infer triggers" x2: added `#[trigger]` on `inset(..)`.

## Effort
About 25 min wall-clock, 8 verify runs. File: 142 lines total, about 55 lines of exec code, about 70 lines of spec/proof (most in from_range).

## Rerun
```
/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus /hdd1/sichangheagent/vl_meeting_work/out/vlm_servo/jit_piece/bitset.rs
```
Output: `verification results:: 17 verified, 0 errors`.

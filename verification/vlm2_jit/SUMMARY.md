# vlm2_jit: JIT targets 1-3 and cranelift-bitset recheck
(authored by agents unless marked 🧑)

Takeaway: targets 1-3 each have a small machine-checked result. Each check also fails on a buggy variant shaped like the matching CVE, so it can catch that bug class. All three are models or rule transcriptions, not checks of real engine code.

- bitset recheck (`bitset_check/RESULT.md`): the bug is confirmed on crates.io 0.137.1 and wasmtime main.
  - `ScalarBitSet::<u64>::from_range(64,64)` panics in a debug build ("attempt to shift left with overflow", scalar.rs:140).
  - A release build returns the full set instead of the empty set.
  - Not reported upstream.
- t1 side effects (`t1_side_effects/REPORT.md`): a z3 model of the effect-chain walk in V8's map inference, checked exhaustively on op sequences up to length 4.
  - The 8.0 code gives 396 violations. The smallest is CheckMaps then JSCreate, the CVE-2020-6418 shape.
  - The main code gives 0 violations. This is a bounded check, not a proof.
- t2 typer (`t2_typer/REPORT.md`): z3 finds all 10 V8 operation-typer.cc integer range rules sound (main 3a06b466).
  - 4 deliberately broken rule variants give concrete counterexamples.
  - Doubles are modeled as exact integers: no NaN, -0, infinities or values beyond 2^53. Emitted machine code, where CVE-2021-21220 lives, is not checked.
- t3 cross-phase (`t3_cross_phase/REPORT.md`): a Verus proof on a toy IR the agent wrote.
  - An allocation-fold pass with a "no Call between" guard keeps the elided-barrier invariant.
  - Without the guard the proof fails, with the witness [Alloc 1, Call, Alloc 2, Store(2, elided)].
  - The IR has no control flow.

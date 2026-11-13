# vlm2_iso: targets 5, 6, 10 (sandbox memory, tab isolation, Servo rooting)
(authored by agents unless marked 🧑)

Labels: [F] ran here, [I] inference. Every result below is about a small model, not real engine code. Experiments stopped on the owner's quota rule; all output is local, nothing published.

## Target 6: same-process tab isolation
- [F] Verus (`tabiso_verus/`): the round-1 two-realm heap model, ported with a `Vec` heap, is proved for any heap size and any op sequence: `24 verified, 0 errors`, about 3 s.
  - Proved: alloc, store (barrier), share, import and a per-realm free all keep the invariant. The isolation theorem: whatever realm r reaches is r-owned or Shared, and Shared points only to Shared.
  - Without the barrier, Verus rejects the model (`16 verified, 3 errors`).
- [F] Kani (`tabiso_kani/`): bounded check, up to 12 steps.
  - With the barrier: holds up to 12 steps on a fixed-size bitmask port. Runtime grows steeply: 6 s at 3 steps, 1354 s at 12 steps.
  - Without the barrier: counterexample at 3 steps.
  - The original `Vec` model reached only 2 steps; 3 of its 4 runs gave no verdict.
- [I] Verus suits this model better than Kani: it gives an unbounded proof in seconds.

## Target 5: sandbox memory confinement
- [F] Verus (`sandbox_verus/`), model of one V8 external-pointer table:
  - Proved: for any attacker write sequence inside the cage, a dereference that does not trap returns an entry of exactly the expected type tag.
  - The proof needs the valid tags to form an antichain: no tag's bits are a subset of another tag's. A control with arbitrary tags fails to verify. V8's real tag constants were not checked against this.
  - Prior work: one search found no verification of V8's table, so absence is not established.
- [F] Wasm bounds-check model (`wasm_mem.rs`): the correct lowering is proved in-bounds. Verus rejects the CVE-2023-26489-style lowering.

## Target 10: Servo GC rooting
- [F] Kani (`servo_rooting/`), mock model of Servo's rooting API: all 4 harnesses pass. Servo was read from a shallow clone, not built.
  - Trace: a derive-style trace marks every field holding a GC pointer. A trace that skips a field is caught.
  - Drop: the #24621 pattern (a destructor reading another GC object during the final GC) is caught in one of the two sweep orders. A compliant destructor passes in both.
- [F] Servo's lint "crown" checks rooting in struct fields. No lint on what a destructor touches was found, but not every lint was audited.
- [F] Issue #15318 has a different shape (an object dropped at teardown after the GC) and is not modeled.
- Next step [I]: a crown-style compiler lint that flags destructors reaching GC objects.

## Common gap
- No result touches real V8, Servo or engine code.
- Not covered: side channels (Spectre), concurrency, moving GC.
- Each subdirectory's `REPORT.md` has rerun commands, verbatim errors and its full list of uncovered items.

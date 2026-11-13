# Boa GC mutation audit
(authored by agents unless marked 🧑)

The concrete Boa finalizer fix is **unmapped as a whole** to the existing proofs. One mutation of its abstract marking rule is **killed**, but this is not a verified rejection of the full buggy implementation. No new safety contract was added.

## Evidence and reruns

The confirmed patch is [boa_gc_finalizer.patch](../../cx_boagcfix/boa_gc_finalizer.patch). Its [report](../../cx_boagcfix/REPORT.md) says: “Both supplied reproducer sources fail with use-after-free on the unchanged revision and pass Miri with the patch.” These Miri results were not rerun here; no builds were performed. Available memory before verification was 114 GiB.

Existing [boa_roots.rs](../../cx_gc/artifacts/proofs/boa_roots.rs) explicitly models the buggy count rule:

```rust
pub open spec fn boa_pass2_rooted(indeg: nat, clones: nat, moved: nat) -> bool {
    indeg < rc_after_finalize(indeg, clones, moved)
}
proof fn thm_resurrection_uaf(indeg: nat, clones: nat, moved: nat)
    requires moved <= indeg, 0 < clones + moved <= indeg
    ensures live_after_finalize(clones, moved) && !boa_pass2_rooted(indeg, clones, moved)
{}
```

The unchanged file verifies: “verification results:: 13 verified, 0 errors” ([log](boa_roots.log)). It proves the bug, rather than asserting a safe collection contract. Calling this a kill merely because its theorem describes a UAF would conflate bug characterization with verifier rejection. Its copy under `out/vlm2_boagc/final/proofs/boa_roots.rs` is byte-identical; `out/vlm2_gc` does not exist.

Existing [boa_mark.rs](../../cx_gc/artifacts/proofs/boa_mark.rs) verifies: “verification results:: 11 verified, 0 errors” ([log](boa_mark.log)). Its abstraction explicitly supplies “`rooted[i] <-> node_ref.is_rooted()` (computed earlier by trace_non_roots)”. Correct marking given supplied roots does not establish those roots remain correct after finalization. Classify the concrete finalizer mutation as outside this contract, not killed.

Later [boa_resurrection_fix.rs](../../vlm3_review/job1/boa_resurrection_fix.rs) verifies: “verification results:: 4 verified, 0 errors” ([log](boa_resurrection_fix.log)). It supplies an existing safety requirement:

```rust
safe_sweep(kept_fixed(succ2, roots2), succ2, roots2)
subset(roots2, kept_fixed(succ2, roots2))
```

I copied that file and changed only `kept_fixed` from `reach(succ2, roots2)` to `reach(succ2, none())`, preserving all contracts and proof bodies: [mutant](boa_resurrection_stale_empty_roots.rs). This represents the existing clone-child witness with empty pre-finalizer roots and unchanged graph. It does not represent every behavior of the old collector. Verus rejects it with “error: postcondition not satisfied” for `safe_sweep` and published-root retention, and “verification results:: 2 verified, 2 errors” ([log](boa_resurrection_stale_empty_roots.log), process exit 1). Classification: **killed abstract mutation**, 1/1 attempted in this narrow category.

Rerun any file with `timeout 60s tools/verus-x86-linux/verus --triggers-mode silent FILE` from the workspace root. The GLIBC weak-version diagnostic is present even on passing runs.

## Why the real diff remains unmapped

The later proof's own [report](../../vlm3_review/job1/REPORT.md), “Not done, and why,” says: “I did not model `ref_count`, `non_root_count`, `Gc::finalize` decrementing, or `DropGuard`. So I did not prove that \"fresh recompute from counts\" equals \"roots = boxes with external handles\". That equivalence is assumed.”

The real patch changes those exact mechanisms, plus repeated finalization and accounting for handles in dead allocations. Reverting those parts cannot alter the later abstract proof: they have no representation there. The original root proof represents the bad decrement/count arithmetic, but no existing proof composes the patched count maintenance with post-finalizer root inference and sweep safety.

Do not count this as one concrete fix killed, or count unaffected passing proofs as concrete survivors. The defensible totals here are: **one concrete fix audited, zero fully mapped, one abstract mutation tested and killed**. The practical gap is connecting actual count updates to the abstract roots; adding more graph-only marking proofs would not close it. This looks worth pursuing if the next experiment targets that connection.

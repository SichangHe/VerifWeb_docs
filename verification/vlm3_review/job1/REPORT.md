# Verus proofs for the cranelift-bitset and boa_gc fixes
(authored by agents unless marked 🧑)

Nothing was filed upstream. Everything is under `/hdd1/sichangheagent/vl_meeting_work/out/vlm3_review/job1/`. Verus 0.2026.11.02.8bf68ee, z3 swapped to 4.16.0 as noted in `out/vlm_servo/SUMMARY.md`. Every Verus run prints a harmless `GLIBC_2.39 weak version` line on stderr; it is stripped from the verbatim blocks below but remains in the .log files.

## 1. ScalarBitSet::from_range

Bug (fact, from `out/cloud/p3_bitset_bug_independent.md`): `from_range(cap, cap)` evaluates `one << lo` with `lo == cap`, which panics in debug and returns the full set in release.

Minimal fix (guard `lo_rng` exactly as upstream already guards `hi_rng`). Replace line 140 of `cranelift/bitset/src/scalar.rs`:
```rust
-        let lo_rng = (one << lo) - one;
+        let lo_rng = if lo >= 1 {
+            (one << (lo - 1)) + ((one << (lo - 1)) - one)
+        } else {
+            T::from(0)
+        };
```
(Equivalent alternative: early-return the empty set when `lo == hi`.) The patch is not applied to any checkout; it is proved on a u64 model.

Files:
- `bitset_from_range.rs`: fixed version and all lemmas. Verifies.
- `bitset_original_fails.rs`: same file plus the original unguarded `from_range_original`. Fails, as intended.
- Logs: `bitset_from_range.log`, `bitset_original_fails.log`.

Commands (cwd = the job1 directory):
```
V=/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus
$V --triggers-mode silent bitset_from_range.rs
$V --triggers-mode silent bitset_original_fails.rs
```
Verbatim output, fixed:
```
verification results:: 13 verified, 0 errors
```
Verbatim output, original (exit 1):
```
note: function body check: not all errors may have been reported; rerun with a higher value for --multiple-errors to find other potential errors in this function
  --> bitset_original_fails.rs:62:1
   |
62 | fn from_range_original(lo: u8, hi: u8) -> (r: u64)
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

error: possible bit shift underflow/overflow
  --> bitset_original_fails.rs:68:23
   |
68 |     let lo_rng: u64 = (one << lo) - one;   // EXPECTED ERROR: shift out of range when lo == 64
   |                       ^^^^^^^^^^^

error: possible arithmetic underflow/overflow
  --> bitset_original_fails.rs:68:23
   |
68 |     let lo_rng: u64 = (one << lo) - one;   // EXPECTED ERROR: shift out of range when lo == 64
   |                       ^^^^^^^^^^^^^^^^^

verification results:: 13 verified, 1 errors
error: aborting due to 2 previous errors
```

What is proved:
- `from_range_fixed`: for all `lo <= hi <= 64`, no shift or arithmetic overflow occurs, and the result `r` satisfies `forall i. has(r,i) <==> lo <= i < hi`, where `has(r,i)` means bit `i` of `r` is 1. So it returns exactly {lo..hi}, including the empty set at `(64,64)`. The core step (`lemma_range`) is a bit-vector proof over all `lo, hi, i`, so it is not tested on samples.
- `from_range_original` with the same spec: Verus cannot prove the shift amount `lo` is `< 64`. The requires clause admits `lo == 64`.
- `from_range_original_lo_lt_cap` (in the passing file): the original arithmetic is correct when `lo < 64`. So the defect is exactly `lo == cap`, which means `lo == hi == cap`.
- `original_wrong_at_cap`: under release-mode wrapping-shift semantics (`1 << 64 == 1`), the original at `(64,64)` yields `0xffff_ffff_ffff_ffff`, so all 64 members are present where the empty set is required.
- `fixed_empty_at_cap`: calls the fixed function at `(64,64)` and `(0,64)` and asserts empty and full, respectively.

## 2. boa_gc finalizer resurrection

Bug (from `out/vlm2_boagc/report.md` and `out/cloud/p1_gc_marking.md` §4): finalizers run between two mark passes. Pass 2 reuses stale pass-1 marks and root counts. A box that a finalizer makes reachable again is freed anyway, leaving a dangling handle.

Fixed rule (the proposal in p1 §4, which I have not tested on boa source): pass 2 is a fresh mark from the post-finalizer roots.

File: `boa_resurrection_fix.rs`; log: `boa_resurrection_fix.log`.
```
$V --triggers-mode silent boa_resurrection_fix.rs
```
Verbatim output:
```
verification results:: 4 verified, 0 errors
```
Model: boxes are ints, `succ(v)` is the set of boxes v holds handles to, `roots` is the set of boxes with external handles, and `reach` is the least closed set (what a correct mark computes). The finalizer is modeled as arbitrary: it leaves any well-formed heap `(succ2, roots2)` over the same boxes.

What is proved:
- `fixed_rule_correct` (Theorem 1): for any finalizer behavior, `kept = reach(succ2, roots2)` has no dangling root or edge. Every root published by a finalizer is kept, and so is everything reachable from it. Only allocated boxes are kept, and `kept` is the smallest closed set.
- `buggy_rule_dangles_clone_child` (Theorem 2): on the Miri `clone-child` scenario (0 -> 1, no roots, finalizer publishes a root to 1), stale marks keep nothing and the sweep is unsafe. The fixed rule keeps box 1 and is safe.
- `buggy_rule_safe_implies_no_resurrection` (Theorem 3): with stale marks, a safe sweep implies nothing was resurrected. The buggy rule is therefore correct only when finalizers never publish.

Sanity check: replacing `kept_fixed` with `reach(succ2, none())` makes the file fail (`2 verified, 2 errors`), so the theorems are not vacuous.

## 3. Not done, and why
- The Rust shown above is not compiled against the cranelift-bitset crate. The proof is on a u64 model, because Verus cannot handle the generic `T: Into<u64>`-style numeric trait. Widths other than 64 are assumed to follow by the same argument (inference, not proved).
- The boa model is set-based. I did not model `ref_count`, `non_root_count`, `Gc::finalize` decrementing, or `DropGuard`. So I did not prove that "fresh recompute from counts" equals "roots = boxes with external handles". That equivalence is assumed. The model also does not check that the real patch is implementable, and the p1 caveat about `Gc::drop` skipping `dec_ref_count` during sweep is untouched.
- I did not run Miri on a patched boa_gc, so there is no end-to-end confirmation that the fix removes the use-after-free.
- Not proved: that the fixed pass 2 terminates or costs no more than the old one.

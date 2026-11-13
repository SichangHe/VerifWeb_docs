# cx_gc: independent review of the boa_gc claims
(authored by agents unless marked 🧑)

Scope: `out/vlm2_boagc/report.md` (vlm2), `out/cloud/p1_gc_marking.md` (p1), §2 of `out/vlm3_review/job1/REPORT.md` (vlm3).
Everything below was re-run in `out/cx_gc/` (cloud code copied to `artifacts/` first). Nothing filed upstream.
Tools: Verus `tools/verus-x86-linux` (z3 4.16.0 swap), Miri nightly, boa git main @ 329e8974 and crates.io 0.21.0 / 0.22.0.

## Bottom line
- the use-after-free (UAF) is real: confirmed on 0.21.0, 0.22.0, main, all 3 modes
- all Verus numbers reproduce exactly; all 7 mutants fail
- p1's root-cause formula (F1) is confirmed by a new experiment (below)
- two overstatements, one slightly wrong quote; no claim found wrong in substance

## Re-run results (fact)
- Miri, p1 repro (`artifacts/miri_repro`), modes move-self / clone-self / clone-child × {0.21.0, 0.22.0, main}: all 9 report
  `error: Undefined Behavior: constructing invalid value of type &boa_gc::GcBox<…>: encountered a dangling reference (use-after-free)`
  - logs: `{0.21.0,0.22.0,main}_{mode}.log`; p1 said clone-self on 0.22.0 was untested; it fails too
- p1 repro file: 0 occurrences of `unsafe` (grep) → "safe Rust only" confirmed
- vlm2 independent repro (`repro/`, `r_0.22.0/`, `r_main/`): UB on all three (logs/)
- Verus, p1 proofs: boa_mark 11, boa_roots 13, boa_ephemeron 15, incremental 9 verified, 0 errors (=48); no assume/admit/external_body
- mutants m1–m7: each ≥1 error (m1 10/1, m2 9/2, m3 10/1, m4 12/1, m5 9/1, m6 14/1, m7 14/1)
- vlm3 `boa_resurrection_fix.rs`: `4 verified, 0 errors`; its mutant (`fix_mutant.rs`, roots2 := none): `2 verified, 2 errors` — matches vlm3

## New test of F1 ("pass-2 rooted iff clones + moved > indeg") (fact)
- prediction: publishing 2 handles to a box with 1 heap in-edge should be safe; publishing 1 should UAF
- `two_clones/`: parent finalizer pushes 2 clones of its child (indeg 1) → Miri clean, prints `child.v=0xc0ffee` twice (`logs/two_clones_rerun.log`)
  - the older `logs/two_clones.log` from the cut-off attempt ran a different binary; ignore it
- `counterexample/` clone-self with 2 self-clones (indeg 1) → Miri clean; 1 clone → UAF
- so the threshold behaves exactly as F1 says

## Source facts (checked at main 329e8974, `core/gc/src/`)
- `is_rooted` = `self.non_root_count() < self.ref_count()` (internals/gc_header.rs:108-109) ✔
- `collect`: `trace_non_roots` once (lib.rs:228), mark, `finalize` (240), `mark_heap` again (243-244); marks/non_root_counts reset only in sweep (lib.rs:457-458, 482-483) ✔
- `impl Finalize for Gc<T>` calls `self.inner_ptr.as_ref().dec_ref_count()` (pointers/gc.rs:320-325) ✔
- lib.rs:211-215 phase comment quoted by p1 ✔

## Issues found
1. overstated (p1 §4): "A finalizer can only reach v through a handle stored in a dead box, so indeg ≥ 1. Publishing a single handle therefore always produces the use-after-free."
   - "only" is unproven: e.g. upgrading a weak/ephemeron reference held outside the heap could reach v with indeg 0 (not tested)
   - accurate wording: "if v is reached via a strong handle held in a dead box"
2. overstated context (p1 §4, "Relevant upstream context"): #5567's "Remove `root_count`, `non_root_count` and `trace_non_roots`" item is under a prototype of `mark_sweep_branded::Gc<'gc, T>` "in oscars", verbatim:
   "- [ ] Make `mark_sweep_branded::Gc<'gc, T>` `Copy` again. Remove `root_count`, `non_root_count` and `trace_non_roots`, and drop `trace_non_roots` from the `Trace` contract."
   (jasonwilliams, 2026-10-10, https://github.com/boa-dev/boa/issues/5567); it is a plan for a new collector, not a fix to boa_gc
3. misquote (p1): "In the current collector, Gc::finalize() decrements the reference count."; actual (mansiverma897993, 2026-10-17, same issue): "In the current collector, Gc<T>::finalize() [decrements the reference count](…)" — meaning unchanged
4. scope of the fix proof (vlm3), already disclosed by vlm3 and correct as disclosed:
   - proves a set-level rule (pass 2 = fresh reachability from post-finalizer roots) is safe
   - does not prove the count-based recompute equals "roots = external handles" after finalization, nor that the `Gc::finalize` decrement / `DropGuard` change is implementable; no patched-boa Miri run
   - so "fix proof" ≠ "the proposed boa patch is proven"; nobody has tested a patch
5. vlm2's "no existing boa report" and p1's search claim: re-checked saved searches (`sources/search_*.txt`); consistent, but absence-of-evidence only
6. p1 Verus model-fidelity claims (index abstraction matches `mark_heap`/`trace_non_roots`): spot-checked structure only; faithful porting of every branch is unverifiable without a line-by-line audit

## External quotes re-checked (✔ = text matches saved fetch in `sources/`)
- rust-gc #124 ✔, open, created 2021-01-26: "The program below uses a finalizer to resurrect a dead object by linking it back to a root." https://github.com/Manishearth/rust-gc/issues/124
- boa PR #4107 ✔: "This allows enabling the sm test suite which was throwing a SIGSEGV on memory usage."
- V8 CVE-2021-37975 ✔: "live objects may remain unmarked and be collected, leading to use-after-free."
- #5567 comment ✔: "an object without a finalizer can become reachable through another object's finalizer."
- other §5 CVE quotes: not re-checked beyond the saved files (unverifiable here)

## Not done
- no Miri run on a patched boa_gc
- not checked: whether boa_engine JS can trigger it (p1 labels this INFERENCE; I have no evidence either way)

# Target 3: compiler phases preserve cross-phase invariants
(authored by agents unless marked 🧑)

## Modeled
A toy straight-line IR, not a real JIT. Ops: `Alloc(o)`, `Call` (any GC-capable node), `Nop`, `Store(o, elided)`.
Motivation (as given in the task, CVE not independently checked by me): CVE-2021-4102, a later phase removed a node after write-barrier elision was decided. No upstream code was read; the model is my abstraction.

- Phase 1 (decision, not modeled as code, assumed): barrier elided on a store.
- Phase 2 (modeled): allocation folding. `Alloc(b)` merges into earlier `Alloc(a)`: `Alloc(b)` becomes `Nop`, uses of `b` are renamed `a`.

## Invariant
`inv(ops)`: every `Store(o, true)` at index i has some j<i with `ops[j]==Alloc(o)` and no `Call` at any k in (j,i).
Also assumed `uniq`: each object is allocated at most once (SSA).

## Result
Correct pass, with guard "no `Call` between `Alloc(a)` and `Alloc(b)`": `fold_preserves` proves `inv(fold(ops,a,b))`.
Verified output:
```
verification results:: 2 verified, 0 errors
```
(2 = `fold_preserves` + `counterexample`.)

Buggy variant, guard dropped (`buggy.rs`, `fold_unguarded`): Verus fails exactly at the "no Call between" step:
```
error: assertion failed
  --> ./buggy.rs:89:32
   |
89 |                         assert(ops[k] != Op::Call);
   |                                ^^^^^^^^^^^^^^^^^^ assertion failed

verification results:: 2 verified, 1 errors
```
Concrete witness, also verified (`counterexample`): `[Alloc 1, Call, Alloc 2, Store(2,elided)]` satisfies `inv`; unguarded fold gives `[Alloc 1, Call, Nop, Store(1,elided)]`, which provably violates `inv` (object now allocated before the Call, so it may have moved: elided barrier unsound).

## Rerun
`/hdd1/sichangheagent/vl_meeting_work/out/vlm2_jit/t3_cross_phase/run.sh`
(Verus at `tools/verus-x86-linux/verus`, z3 swapped per `out/vlm_servo/SUMMARY.md`. The "GLIBC_2.39" warning on stderr is filtered by the script.)

## Limitations
- Toy IR: no control flow, no real object layout, no moving-GC semantics (a `Call` simply kills the young-allocation property).
- Only one later pass (folding), one fold at a time, proof is for a single (a,b) pair; no DCE or removal-pass proof. The CVE's specific "node removal" pass is not modeled.
- Phase 1 correctness (that elision is chosen soundly) is not modeled; only preservation of its output invariant.
- Not done: Cranelift egraph / pcc on real code.
- Files: `model.rs` (correct), `buggy.rs` (buggy), `run.sh`.

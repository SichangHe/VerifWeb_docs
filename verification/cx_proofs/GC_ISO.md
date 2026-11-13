# GC, scheduling, isolation, and cross-phase proof audit
(authored by agents unless marked 🧑)

All 23 distinct source files were rerun with `tools/verus-x86-linux/verus <file> --multiple-errors 10`; every count matches `results.json`. Identical copies are listed below. Logs are in `gc_iso_logs/`. “Sound” means no unsoundness found in the stated abstract theorem; it does not certify Verus, vstd, Rust, or a real engine. Negative controls are rejected, not passing unsound proofs.

## Findings

1. **Overstated ephemeron precision.** `out/cx_gc/artifacts/proofs/boa_ephemeron.rs:11–14` says:

   > // Proven: termination; on return every rooted node is marked, the marked set is closed
   > // under edges (fixpoint), hence every node reachable from a rooted node is marked;
   > // and conversely every marked node is reachable (no over-retention).

   Its opening comment already contradicts the last claim:

   > // Verus model of boa_gc's ephemeron (weak) mark phase. Shares the worklist model with boa_mark.rs
   > // (soundness/precision part removed: ephemeron values are not strongly reachable).

   `mark_heap_weak` actually ensures only length, roots marked, strong-edge closure, and ephemeron closure. Checked witness: two nodes, no strong edges, node 0 rooted, ephemeron `(0,0,1)`. The conditions force node 1 marked although `reachable(edges, roots, 1)` is false. `ephemeron_precision_probe.rs` adds a proof of the concrete state and non-reachability; log: “verification results:: 16 verified, 0 errors”. This is a false source comment, not a logical inconsistency in the verified contract. Delete the precision claim or define/prove reachability including ephemeron rules.

2. **Scheduler proof remains an abstraction and partial correctness.** The trusted item is exactly (`out/cx_loop/verus/event_loop.rs:14–16`, also original):

   ```rust
   // Oracle: the JS callback runs and returns what it enqueued. No spec => any output.
   #[verifier::external_body]
   fn run_job(id: u64) -> (out: Vec<Item>) { unimplemented!() }
   ```

   There is no trusted postcondition or precondition. It cannot assert that callbacks terminate, preserve a real JavaScript heap, or return any particular jobs. The appended `fn oracle_false_probe() { let out = run_job(0); assert(false); }` was rejected: “verification results:: 10 verified, 1 errors”; exact error: “assertion failed”. No contradiction found. The stub panics if executed; the verified scheduler result concerns any returned vector. `#[verifier::exec_allows_no_decreases_clause]` permits nontermination and is not an axiom proving false.

   `out/cx_loop/REVIEW.md`, “Actionable findings”, quotes the source report headline “the patched loop is verified in Verus” and its limitation “Nothing mechanically links them to `job.rs`, so the abstraction gap is unverified.” The model verifies FIFO/empty-microtask-at-timer-start, not real-patch correctness or termination. Verdict: sound abstract theorem; overstated implementation headline.

3. **Root-resurrection wording exceeds its formula.** `boa_roots.rs:156–160` says:

   > // Theorem F2: hence every resurrection with 0 < clones + moved <= indeg is a use-after-free
   > // (v is unrooted in pass 2 and unmarked; if no rooted box reaches it, sweep frees it while a live
   > // handle exists). Since a finalizer can only obtain a handle to v by reading one stored in a dead
   > // box, indeg >= 1 for every resurrectable v, so publishing a single handle always hits this case.

   The actual contract is `ensures live_after_finalize(clones, moved) && !boa_pass2_rooted(indeg, clones, moved)`. It proves a live handle plus failure of the direct root test, not a sweep or reachability fact. Another rooted object can reach the target. The parenthetical is necessary; the unconditional headline is overstated. The arithmetic theorem itself is sound, with nonvacuous witness `(indeg,clones,moved)=(1,1,0)`. The file's `assert(false)` is inside the unreachable saturation branch, justified by exact reference-count preconditions, not an assumption.

## Other contracts and vacuity

- `boa_mark.rs`: `mark_heap` requires only well-formed edges and proves both reachability directions, with terminating loops. A one-node rooted graph satisfies its precondition; no contradictory requirement found.
- `boa_ephemeron.rs`: one-node rooted graphs and well-formed ephemerons satisfy its requirements. Precision is absent as above; closure is meaningful.
- `incremental.rs`: contains no trusted axiom. Its explicit example begins with `seq![Color::Black, Color::Gray, Color::White]` and proves `inv(s0)`, then shows the no-barrier transition breaks it. The introductory limitation is explicit: “every live pointer is reachable from the single root object (no unrooted stack pointers).” This is an abstraction assumption, not verified gc-arena implementation behavior.
- `boa_resurrection_fix.rs`: `kept_fixed` is defined as `reach(succ2, roots2)`, and `safe_sweep` as roots retained plus edge closure. The proof establishes precisely that mathematical rule. It does not establish root recomputation, reference counts, or a concrete patch. `wf` is satisfiable (empty heap, and the two-object clone-child example); no vacuity found. `out/cx_gc/REVIEW.md` explicitly says “does not prove the count-based recompute equals 'roots = external handles' after finalization”.
- `event_loop.rs`: a queue with one microtask, zero timers, both heads zero, and empty started sequence satisfies `inv`; timer preconditions are satisfiable with an empty microtask queue and one timer. The function checks the requested property at every timer call, rather than assuming the whole scheduler correct.
- `ept.rs`: no trusted language construct. A one-entry table with payload 0 and tag `0xff00` satisfies `inv`; valid expected tags are nonempty. `main_theorem` proves payload/tag membership, not liveness, ownership, or provenance. The comment “a table entry that was installed by a trusted op with tag exactly x” is stronger than its contract: the initial good state is arbitrary and `ops` may be empty. That provenance must include an assumption about initial entries. The report accurately states: “The cage as `Map<u64,u8>` plays no role in the proof except as the thing the attacker writes; the model proves independence of table from it by construction (separate fields), which is the assumption, not a theorem about memory layout.” Treat actual theorem as sound; provenance comment as overstated.
- `wasm_mem.rs`: no trust. Requirements `k ∈ {1,2,4,8}` and `1 <= n <= 16` have many witnesses; safety is relative to the chosen reserved region. Correct variant verifies; `-- --cfg buggy` independently reran with “verification results:: 5 verified, 1 errors”, rejecting both claimed bounds and exact semantics. The report explicitly excludes real engine code.
- `heap.rs`: no trust. `new` establishes the invariant and `alloc` creates a rooted object; a concrete one-object heap with root `(0,0)` and owner `Realm(0)` satisfies both invariant and a length-one reachability path. Operations preserve the local invariant; isolation is derived by path induction. No impossible precondition found. Successful `free` is possible from an arbitrary invariant heap without roots, but not from `new` using only these methods: every allocation adds a permanent root and no operation deletes roots. The report already disclaims garbage-collection liveness. All object fields are public, so arbitrary Rust clients are not forced through these methods; the theorem requires `inv` explicitly.
- `t3_cross_phase/model.rs`: no trust. `[Alloc(1), Alloc(2), Store(2,true)]` meets the guarded fold's requirements. The report accurately says “A toy straight-line IR, not a real JIT” and “Phase 1 correctness (that elision is chosen soundly) is not modeled; only preservation of its output invariant.”

No `assume`, `assume_specification`, `admit`, verifier external declarations, or user axioms occur in these proof groups apart from the scheduler oracle. Ordinary uses of “external” in comments are not trusted items. All precondition checks above are source reasoning, except explicit checked witnesses already present or in the new probe; this was not an exhaustive automated satisfiability proof of every helper contract.

## Per-file rerun inventory

Each entry lists verified/error counts, trusted items, and verdict. Counts apply to every byte-identical path on that entry. Logs use the representative basename plus the first six hash digits from `gc_iso_results.json`.

- 15 verified / 0 errors; trusted: none; verdict: overstated comment; sound stated contract
  - `out/cx_gc/artifacts/proofs/boa_ephemeron.rs`
  - `out/cx_gc/proofs/boa_ephemeron.rs`
  - `out/vlm2_boagc/final/proofs/boa_ephemeron.rs`
- 11 verified / 0 errors; trusted: none; verdict: sound within stated model
  - `out/cx_gc/artifacts/proofs/boa_mark.rs`
  - `out/cx_gc/proofs/boa_mark.rs`
  - `out/vlm2_boagc/final/proofs/boa_mark.rs`
- 13 verified / 0 errors; trusted: none; verdict: overstated comment; sound stated contract
  - `out/cx_gc/artifacts/proofs/boa_roots.rs`
  - `out/cx_gc/proofs/boa_roots.rs`
  - `out/vlm2_boagc/final/proofs/boa_roots.rs`
- 9 verified / 0 errors; trusted: none; verdict: sound within stated model
  - `out/cx_gc/artifacts/proofs/incremental.rs`
  - `out/cx_gc/proofs/incremental.rs`
  - `out/vlm2_boagc/final/proofs/incremental.rs`
- 10 verified / 1 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/cx_gc/artifacts/proofs/mutants/m1.rs`
  - `out/cx_gc/proofs/mutants/m1.rs`
  - `out/vlm2_boagc/final/proofs/mutants/m1.rs`
- 9 verified / 2 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/cx_gc/artifacts/proofs/mutants/m2.rs`
  - `out/cx_gc/proofs/mutants/m2.rs`
  - `out/vlm2_boagc/final/proofs/mutants/m2.rs`
- 10 verified / 1 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/cx_gc/artifacts/proofs/mutants/m3.rs`
  - `out/cx_gc/proofs/mutants/m3.rs`
  - `out/vlm2_boagc/final/proofs/mutants/m3.rs`
- 12 verified / 1 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/cx_gc/artifacts/proofs/mutants/m4.rs`
  - `out/cx_gc/proofs/mutants/m4.rs`
  - `out/vlm2_boagc/final/proofs/mutants/m4.rs`
- 9 verified / 1 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/cx_gc/artifacts/proofs/mutants/m5.rs`
  - `out/cx_gc/proofs/mutants/m5.rs`
  - `out/vlm2_boagc/final/proofs/mutants/m5.rs`
- 14 verified / 1 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/cx_gc/artifacts/proofs/mutants/m6.rs`
  - `out/cx_gc/proofs/mutants/m6.rs`
  - `out/vlm2_boagc/final/proofs/mutants/m6.rs`
- 14 verified / 1 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/cx_gc/artifacts/proofs/mutants/m7.rs`
  - `out/cx_gc/proofs/mutants/m7.rs`
  - `out/vlm2_boagc/final/proofs/mutants/m7.rs`
- 4 verified / 0 errors; trusted: none; verdict: sound within stated model
  - `out/cx_gc/boa_resurrection_fix.rs`
  - `out/cx_gc/proofs/boa_resurrection_fix.rs`
  - `out/vlm3_review/job1/boa_resurrection_fix.rs`
- 2 verified / 2 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/cx_gc/fix_mutant.rs`
- 10 verified / 0 errors; trusted: `run_job` external_body (no contract); verdict: overstated implementation headline; sound model contract
  - `out/cx_loop/verus/event_loop.rs`
  - `out/vlm3_boaloop/bundle/verus/event_loop.rs`
- 13 verified / 1 errors; trusted: `run_job` external_body (no contract); verdict: rejected negative control (not a verified proof)
  - `out/cx_loop/verus/event_loop_original.rs`
  - `out/vlm3_boaloop/bundle/verus/event_loop_original.rs`
- 16 verified / 0 errors; trusted: none; verdict: overstated comment; sound stated contract
  - `out/vlm2_iso/sandbox_verus/ept.rs`
- 14 verified / 2 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/vlm2_iso/sandbox_verus/ept_badtags.rs`
- 6 verified / 0 errors; trusted: none; verdict: sound within stated model
  - `out/vlm2_iso/sandbox_verus/wasm_mem.rs`
- 24 verified / 0 errors; trusted: none; verdict: sound within stated model
  - `out/vlm2_iso/tabiso_verus/heap.rs`
- 16 verified / 3 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/vlm2_iso/tabiso_verus/nobarrier.rs`
- 16 verified / 3 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/vlm2_iso/tabiso_verus/nobarrier_direct.rs`
- 2 verified / 1 errors; trusted: none; verdict: rejected negative control (not a verified proof)
  - `out/vlm2_jit/t3_cross_phase/buggy.rs`
- 2 verified / 0 errors; trusted: none; verdict: sound within stated model
  - `out/vlm2_jit/t3_cross_phase/model.rs`

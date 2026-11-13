# p1_gc_marking: verifying the mark phase of a real Rust GC (boa_gc), plus write-barrier hazards

Authored by agents (one Claude session, plus one research subagent for the bug survey). No human words appear below except inside quoted sources.

Context: this follows up the Nov 3 advisor meeting on agent-driven Verus verification for web, JavaScript and browsers. Everything here uses public sources. All artifacts are in `/home/user/p1_gc_marking/` in the cloud container.

Labels used throughout:
- FACT: observed directly (code, tool output, or quoted source)
- INFERENCE: my reasoning from facts
- BELIEF: a judgment that is not proven

## 1. Takeaways

1. **Verus proofs of boa_gc's marking algorithm are done and verify.** Target: Boa's `boa_gc` at commit `329e8974` (2026-10-31). FACT: four Verus files pass (48 proof obligations, under 2 s each), and seven deliberately buggy variants (mutants) are all rejected. Proven:
   - (a) The stop-the-world mark worklist terminates and reaches a fixpoint. At that fixpoint, everything reachable from a root is marked, and everything marked is reachable.
   - (b) Boa's reference-count-based root inference is exact.
   - (c) Boa's ephemeron fixpoint loop is correct.
   - (d) A gc-arena-style incremental marker keeps the "no black→white edge" invariant under backward or forward write barriers, and loses it without one.
2. **I found a real use-after-free in boa_gc reachable from safe Rust: finalizer resurrection.**
   - FACT: Miri (Rust's undefined-behavior checker) reports "dangling reference (use-after-free)" in boa_gc 0.21.0, 0.22.0 (latest on crates.io) and `main`. The trigger is a `Finalize` impl that clones or moves a `Gc` handle out of a dying object.
   - FACT: the repro contains no `unsafe` code.
   - Root cause, as a formula proven in Verus: the second mark pass treats a resurrected object as a root only if finalizers publish more handles to it than it had heap in-edges.
   - The same bug class has been open in rust-gc, the crate boa_gc started from, since 2021 (issue #124).
   - FACT: I have not reported it upstream. That is outward-facing, so it is the human's call.
3. **The proven property would have caught real bugs.** Boa's own ephemeron bug (PR #4107, Jan 2025) violated the property. Mutant m6 re-creates that bug and the proof rejects it. V8's in-the-wild CVE-2021-37975 is the same "fixpoint exits too early" class, and mutant m7 re-creates that shape.
   - INFERENCE: write-barrier CVEs in JIT-emitted code (SpiderMonkey CVE-2026-2767, JSC CVE-2019-8622, V8 CVE-2022-1310) violate invariant (d). Catching them needs (d) checked against the compiler's emitted stores, which this packet does not do.

## 2. Target: how boa_gc marks (all FACT, from source)

boa_gc is single-threaded, stop-the-world and non-incremental, and has no write barriers. From `core/gc/src/lib.rs` (https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/gc/src/lib.rs):

> "This collector currently functions in four main phases / Mark -> Finalize -> Mark -> Sweep / 1. Mark nodes as reachable. / 2. Finalize the unreachable nodes. / 3. Mark again because `Finalize::finalize` can potentially resurrect dead nodes. / 4. Sweep and drop all dead nodes."

Boa has no explicit root set. It works roots out from counts, in `Collector::trace_non_roots`:

> "Count all the handles located in GC heap. Then, we can find whether there is a reference from other places, and they are the roots."

From `core/gc/src/internals/gc_header.rs`:

```rust
pub(crate) fn is_rooted(&self) -> bool {
    self.non_root_count() < self.ref_count()
}
```

The worklist, from `core/gc/src/trace.rs`:

```rust
while let Some(node) = self.queue.pop_front() {
    let node_ref = unsafe { node.as_ref() };
    if node_ref.is_marked() { continue; }
    node_ref.header.mark();
    let trace_fn = node_ref.trace_fn();
    unsafe { trace_fn(node, self) }
}
```

`Collector::mark_heap` enqueues every node for which `is_rooted()` holds and drains the queue. It then runs a weak phase: ephemerons are retried with `retain_mut` until `previous_len == pending_ephemerons.len()`.

## 3. Proofs

Files are in `proofs/`. Verus was built from source at commit `d804d56`, with z3 4.16.0. Run: `verus <file>.rs`. The full log is in `verus_results.txt`.

**`boa_mark.rs`: the mark phase (11 obligations verified).**
- Model: an executable Verus port of `mark_heap` (preliminary phase) and `trace_until_empty`. The FIFO queue is a `Vec` plus a head index, matching `VecDeque::pop_front`.
- Abstraction: boxes become indices 0..n. `edges[i]` is what `trace_fn` enqueues. `rooted[i]` is the result of `is_rooted()`.
- Proven postconditions:
  1. every rooted node is marked
  2. `closed`: marked(u) ∧ u→v ⇒ marked(v), i.e. a fixpoint
  3. reachable from a root ⇒ marked. This is the safety property: sweep frees nothing live.
  4. marked ⇒ reachable. Nothing dead is retained.
- Termination: lexicographic measure (number of unmarked nodes, queue length minus head).
- Key loop invariant: the tri-color invariant, where black = marked and gray = still in the queue. No black node points to a white node.
- FACT: the model also compiles and runs on a test graph (`--compile`) and prints the expected marks.

**`boa_roots.rs`: root inference and the second pass (13 obligations verified).**
- R1: an executable port of `trace_non_roots`, including the saturating `inc_non_root_count`. It yields `non_root_count[v] == indeg(v)`, the number of heap handles to v. The saturation branch is proven unreachable (`assert(false)` verifies) on any heap where `ref_count = external handles + heap handles`.
- R2: `is_rooted(v) ⇔` some handle to v lives outside the GC heap.
- F1: for a box that pass 1 found dead, boa's pass-2 root test holds iff `clones + moved > indeg`. Here `clones` is the number of handles finalizers clone out, and `moved` the number they move out.
- F2: so every resurrection with `0 < clones + moved ≤ indeg` leaves a live handle to an unrooted, unmarked box. Section 4 covers this.
- `hazard_double_count`: an obligation on manual `unsafe impl Trace`. If `trace_non_roots` counts an edge twice, the saturation cap does not prevent a real root from being classified as non-root.

**`boa_ephemeron.rs`: the weak phase, steps 1 and 3 (15 obligations verified).**
- Proven: at exit the marks are closed under strong edges, and they satisfy the ephemeron rule (box marked ∧ key marked ⇒ value marked).
- This means boa's termination test (`previous_len == pending.len()`) is sound. A pass that removes nothing also marks nothing.
- Step 2 (weak maps) is not modeled.

**`incremental.rs`: gc-arena-style incremental marking (9 obligations verified).**
- Model: a state machine over (colors, edge set) with mutator steps between mark steps. Steps follow `kyren/gc-arena@5ea967ab src/context.rs`: `trace`, `mark_one`, `backward_barrier`, `forward_barrier` and `root_barrier`. New objects start White (`gc_ptr.rs`: "color set to `White`").
- Proven:
  - invariant I is preserved by: a mark step, allocation, edge removal, store with backward barrier, store with forward barrier, and root re-gray
  - end of mark (I, no gray objects, root not white) ⇒ every object reachable from the root is black
  - a concrete 3-object store without a barrier ends marking with a reachable White object
  - the same trace with the backward barrier keeps that object alive
- Assumption, not modeled: when a mark step runs, no live pointer exists outside the root. gc-arena enforces this with its `'gc` lifetime. Its source says "at the time of call no Gc pointers can be live that are not reachable from the given root object."

**Mutants: each one is rejected, so the specifications are not vacuous (FACT).**
- m1: never sets the mark bit
- m2: drops the last child edge (a missed trace edge)
- m3: skips root 0 (a missing root)
- m4: `trace_non_roots` counts each edge twice
- m5: claims a store without a barrier preserves I
- m6: an ephemeron value is handled without being marked (the shape of the pre-#4107 bug)
- m7: the ephemeron loop stops after one pass (the shape of V8 CVE-2021-37975)

## 4. Finding: finalizer resurrection is a use-after-free in boa_gc

**Repro.** `miri_repro/src/main.rs` is safe Rust only; the file contains no unsafe blocks or unsafe impls. It has three modes:
- `move-self`: a node moves its self-handle into a `thread_local`
- `clone-self`: a node clones its self-handle out
- `clone-child`: a parent's finalizer clones its handle to a child

Command: `MIRIFLAGS=-Zmiri-disable-isolation cargo +nightly miri run -- <mode>`.

FACT: Miri reported the following for all three modes on `main@329e8974` and crates.io `0.21.0`. On `0.22.0` I tested `move-self` and `clone-child`, and both failed the same way:

```
error: Undefined Behavior: constructing invalid value of type &boa_gc::GcBox<Child>: encountered a dangling reference (use-after-free)
```

FACT: the native build silently reads freed memory (`clone-child: child.payload=0xc0ffee`). An earlier variant panicked with a garbage `GcCell<T> already borrowed`.

**Root cause.** Three facts in the code combine:
1. `non_root_count` is computed once, before pass 1, and pass 2 reuses it.
2. Marks are not cleared between passes.
3. Finalizing a dead box runs `impl Finalize for Gc<T>` on every handle the box still holds. That impl does `self.inner_ptr.as_ref().dec_ref_count()` (`core/gc/src/pointers/gc.rs`).

INFERENCE: a dead box v has `ref_count == indeg` before finalization. Afterwards it has `clones + moved`, while its stale `non_root_count` stays `indeg`. That gives Theorem F1. A finalizer can only reach v through a handle stored in a dead box, so `indeg ≥ 1`. Publishing a single handle therefore always produces the use-after-free.

INFERENCE: this is a write-barrier bug in disguise. Finalization is a mutator that runs between two mark passes with no barrier, and pass 2 re-traces only from stale "roots".

**Prior art.** rust-gc issue #124, "Dead objects resurrected by finalizer are incorrectly deallocated" (andersk, opened 2021-01-26, still open; https://github.com/Manishearth/rust-gc/issues/124):

> "The program below uses a finalizer to resurrect a dead object by linking it back to a root." … "`force_collect` deallocates the object anyway, leading to use after free."

FACT: Boa used rust-gc until 2022. At commit `4d2772d6`, `boa_gc/src/lib.rs` was `pub use gc::{custom_trace, force_collect, … Finalize, Gc, …}`. Boa's own collector arrived in "Boa Gc implementation draft (#2394)" on 2022-11-14.

FACT: searches of Boa's issue tracker for "finalize resurrect" and for issues mentioning "finalizer" found no report of this bug.

**Impact.**
- INFERENCE: JavaScript running on boa_engine probably cannot trigger it. The only engine `Finalize` impls I found that touch other values are `CleanupSignaler` (sends `()` on a channel) and `Map`/`SetIteratorLock` (unlocks a map). Neither publishes a `Gc` handle. FinalizationRegistry callbacks run later as jobs, not inside `finalize`.
- BELIEF: the bug is real for any embedder or crate that uses boa_gc's safe `Finalize` API.

**Relevant upstream context.** Boa issue #5567 (jasonwilliams, 2026-10-10; https://github.com/boa-dev/boa/issues/5567) plans to "Remove `root_count`, `non_root_count` and `trace_non_roots`, and drop `trace_non_roots` from the `Trace` contract." In the same thread, mansiverma897993 (2026-10-17) writes: "In the current collector, Gc::finalize() decrements the reference count."

**Fix (untested proposal).**
- Make pass 2 a fresh collection:
  1. stop decrementing in `Gc::finalize`
  2. clear marks and non-root counts
  3. re-run `trace_non_roots` and `mark_heap` on the post-finalization heap
- Correctness would then follow from R1, R2 and the `mark_heap` theorem, because they are stated for any heap.
- Moving the decrement needs care: `Gc::drop` skips `dec_ref_count` while sweep's `DropGuard` is active.

## 5. Real GC bugs this property class covers

These are quoted from primary sources. ✔ means I re-fetched the source myself. ◇ means the research subagent read it from raw text. ≈ means it was read through a summarizing fetch tool, so the wording may not be exact.

- **Boa PR #4107 ✔ (https://github.com/boa-dev/boa/pull/4107)**, commit "Enable sm test suite and fix ephemeron bug". PR text: "This allows enabling the sm test suite which was throwing a SIGSEGV on memory usage."
  - FACT, from the diff of commit `426503f3`: before the fix, the weak-phase loops ran `while let Some(node) = tracer.next() { … trace_fn(node, tracer); }` and never called `mark()`. Nodes reached only through ephemeron values or weak maps were traced but left unmarked.
  - INFERENCE: this is a direct violation of "reachable ⇒ marked", and mutant m6 has the same shape. The PR does not state outright that the SIGSEGV came from this.
- **V8 CVE-2021-37975 ✔ (https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2021/CVE-2021-37975.md)**: "When handling ephemerons (`WeakMap`, `WeakSet` etc.), a logic bug in the v8 garbage collector means that live objects may remain unmarked and be collected, leading to use-after-free." Also: "some ephemerons in `current_ephemerons` may turn out to be alive when the iteration exits. In this case, these ephemerons will remain unmarked." Class: fixpoint exits early, the m7 shape.
- **SpiderMonkey CVE-2026-2767 ✔ (https://bugzilla.mozilla.org/show_bug.cgi?id=2013741)**, "Missing Pre-Barrier in Baseline `array.fill` Allows Use-After-Free During Incremental GC". Reporter: "During an incremental GC cycle, a black (already-scanned) object can acquire the only remaining reference to a white (not-yet-scanned) object via a sequence involving `array.fill`, causing the GC to collect a live object." bvisness: "We need to use pre-write barriers whenever storing into an already existing GC array."
  - Note: SpiderMonkey uses a snapshot-at-the-beginning deletion barrier. My `incremental.rs` models insertion barriers only.
- **SpiderMonkey CVE-2024-7527 ✔ (https://bugzilla.mozilla.org/show_bug.cgi?id=1871303)**. jcoppeard: "Setting security sensitive because this could result in use after free if we sweep something that should have been marked." Class: sweep began while marking work remained, which violates the fixpoint precondition.
- **JavaScriptCore CVE-2019-8622 ≈ (https://www.exploit-db.com/exploits/46888)**: "if the analysis is incorrect and a GC can happen in between, then the emitted code can cause use-after-free issues". Class: a write barrier was wrongly elided.
- **V8 CVE-2022-1310 ◇ (https://chromium.googlesource.com/v8/v8/+/bdc4f54a50293507d9ef51573bab537883560cc8)**: "Update write barrier when storing HeapNumber to last index." The fix replaces `SKIP_WRITE_BARRIER` with `UPDATE_WRITE_BARRIER`.
- **Wasmtime CVE-2022-24791 ◇ (GHSA-gwc9-348x-qwv2)**: "When Wasmtime would eventually collect garbage, it would fail to find live references on the stack because of the missing stack maps, think that they were unreferenced garbage, and therefore reclaim them." Class: missing root, the m3 shape.
- **gc-arena PR #34 ≈**: the `Hash{Map,Set}` `Collect` impls "accept arbitrary `S: BuildHasher`, but don't trace the value at all." Class: missed trace edge, the m2 shape. No crash was reported.

INFERENCE on coverage: the proofs here cover collector algorithms. JIT barrier elision and stack maps would need the same invariants checked against code generation.

## 6. Blockers and limitations

- Verus release binaries could not be downloaded (`github.com/.../releases` returned 403 through the session proxy). I built Verus from source in about 10 minutes, with z3 4.16.0 from PyPI `z3-solver==4.16.0`.
- The model abstracts real pointers into indices. These parts are not verified:
  - `unsafe` pointer validity
  - individual `Trace` impls: the model assumes `trace` and `trace_non_roots` visit the same handles. For derived impls the macro guarantees this, but not for manual ones.
  - the weak-map step (step 2)
  - `GcRefCell::trace` skipping cells that are currently being written. FACT: it matches on `self.borrow.get().borrowed()`. INFERENCE: this could be another hazard and deserves its own look.
- `incremental.rs` is a model of gc-arena's protocol. It is not a port of gc-arena's code, and it does not model SATB barriers or weak references.
- Nothing was reported upstream.

## 7. Suggested next steps

1. Report the boa_gc bug, or attach it to issue #5567. Needs a human decision.
2. Verify the proposed fix by porting `collect()` end-to-end, reusing the R1/R2 and `mark_heap` lemmas.
3. Add a SATB (Yuasa) deletion-barrier model to cover the SpiderMonkey class.
4. Use Kani to check derived `Trace` impls: `trace` and `trace_non_roots` must visit the same handles.

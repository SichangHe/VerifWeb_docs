# Runtime and tab-isolation independent review
(authored by agents unless marked 🧑)

Reviewed `out/vlm_runtime/SUMMARY.md`, `dynstate/REPORT.md`, `tabiso/REPORT.md`, and their implementations. Reproductions used copies under `runtime_copy/`; originals were unchanged. Lightpanda is covered separately in `lightpanda_review.md`.

## Findings requiring correction

1. **Overstated as JavaScript verification:** “snapshot-specialized → all 3 proved.” The program prints that result, but the executor is unsound even within its advertised arithmetic/identifier subset. `symx.py` returns `None` for an undeclared identifier and uses unbounded Z3 integers for JavaScript numbers. Two copied-script counterexamples both print “PROVED: no exception, no cookie read, loops<=8 iters (within bound 8)”:
   - `var x = missingName;` → Node: “ReferenceError: missingName is not defined”.
   - `var x = 9007199254740992; if (x + 1 === x) { var y = window.coupon.rate; }`, with `coupon:null` → Node: “TypeError: Cannot read properties of null (reading 'rate')”. Integer arithmetic incorrectly prunes the throwing branch.
   Evidence: [counterexample output](dynstate_counterexamples.log), [reproduction driver](runtime_checks.py), copied `runtime_copy/dynstate/symx.py` (`Identifier`, `BinaryExpression`). The particular good-snapshot script does satisfy the three checks under its stated values; the general proof claim is unsupported by this executor. Describe its result as a check of a toy integer model until the semantics are sound.

2. **Wrong:** “bad snapshot → 2 real violations w/ witnesses.” The cookie-read violation is real; the reported array exception is not. Original bad-snapshot script at `qty=4` executes in Node with “no exception; total=NaN”. Ordinary JavaScript array indexing outside the array yields `undefined`; the subsequent addition yields `NaN`. The executor labels and terminates these paths as “EXCEPTION(index out of bounds)”, which can also miss subsequent behavior. Evidence: [counterexample output](dynstate_counterexamples.log) and `symx.py:get`. If array bounds are a separate desired policy, name that policy instead of equating it with exceptions.

3. **Wrong as a live-isolate measurement:** “worker isolate 0.78 MB”. `bench.js` worker branch ends with `parentPort.postMessage(1);return;` and keeps no event-loop work alive. Instrumenting only worker-exit counting and preserving the benchmark yields `"exited_workers":50` at measurement for N=50. Rerun measured 1,299 KB per exited worker, versus the reported 777 KB, but neither is the cost of 50 live isolates. Keep workers alive, retain their data, wait for readiness, and measure again. Evidence: [memory log](tabiso_memory.log), [instrumented copy](runtime_copy/tabiso/mem/bench_instrumented.js).

4. **Overstated:** “Chrome's ~300 MB/tab is mostly DOM/layout/GPU, so engine-only sharing saves little.” Neither Chrome nor its component memory was measured. A small Node workload cannot attribute the memory of a much larger browser workload. The Node experiment supports only a comparison of this particular allocation workload. Contexts are not retained explicitly either; a live-context benchmark must retain them and check lifetime. Evidence: original `tabiso/mem/bench.js`, with context creation `vm.runInContext(PAGE,vm.createContext({}))`; there is no Chrome measurement.

## Claim-by-claim disposition of the summary

### Dynamic state

- **Confirmed:** a Z3 symbolic executor, Acorn parser, integer loop bound 8, and checks labelled no exception/no cookie read/loop bound exist in the inspected code. **Overstated** if their labels imply JavaScript semantic soundness; see findings 1–2.
- **Confirmed as output:** 9 agnostic alarms, zero good-snapshot alarms, two bad-snapshot alarms. Independent rerun: 265.4 ms agnostic; 61.1 ms good snapshot; 80.4 ms bad snapshot. Output includes “paths=4 solver_calls=30” for the good snapshot. [Complete rerun](dynstate_rerun.log).
- **Overstated:** “mostly false for the real page.” The supplied example is a handwritten script and JSON snapshot; no real browser page was captured. Its alarm reduction is demonstrated only for this model.
- **Confirmed:** no mutation guard, no full-JavaScript model, and no real-script measurements in these artifacts. A guard and sound assumptions remain necessary; the counterexamples show the semantics need repair even before broadening the subset.
- **Unverifiable as novelty:** “snapshot as precondition + proof + guard”. The guard was not implemented, the checker is unsound for JavaScript, and no absence-of-prior-work conclusion follows from the experiment. See the separate prior-work review.

### Tab isolation

- **Confirmed, narrow measurement:** Node 22.21.1 rerun at N=50 gives contexts 441 KB and processes 9,225 KB, roughly 21×. Original 437/8,978 KB values are plausible historical measurements, not exact repeatable constants. [Memory output](tabiso_memory.log). Workers are invalid as described above.
- **Confirmed:** Rust two-realm heap with owner labels, a shared space, guarded store/share/import operations, randomized tests. Independent rerun prints “unchecked: 19975/20000 runs violate invariant” and “checked:   0/20000 runs violate invariant”. [Model log](tabiso_model.log).
- **Confirmed scope limit:** this is testing, not proof. The invariant is reachability ownership, not general noninterference. `store` has no acting-realm parameter and assumes trusted access to object handles; it does not establish an engine's complete access control or GC correctness.
- **Confirmed as limitations:** this model contains no speculative-execution model, real engine, JIT, browser bindings, or GC. **Overstated as necessity:** “JIT output needs per-run checking”; a proof of the generator could also establish generated-code safety. Per-run validation is one proposed approach.
- **Unverifiable here:** recalled CVE identifiers and tool-coverage generalizations do not gain evidence from this model. They are explicitly unverified in the report and should remain so.
- **Recommendations, not results:** porting to Verus/Kani, trying QuickJS, capturing CDP snapshots and adding guards are proposed follow-up work. No recommendation was treated as an achieved capability.

## Reproduction

`bash runtime_copy/dynstate/run.sh`; `cargo run --release --manifest-path runtime_copy/tabiso/model/Cargo.toml --target-dir tabiso_build`; `python3 runtime_checks.py` from this review directory's parent paths as appropriate. The Python driver creates only copied test files and terminates its own process groups, including Node children. Compiler/Node outputs quoted above are observations from this review, not external publication claims.

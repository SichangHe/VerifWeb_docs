# boa_gc finalizer fix
(authored by agents unless marked 🧑)

Implemented against `329e89748ed34e218fe593b4209b1dbe1d6eb64d` in [boa](boa). Both supplied reproducer sources fail with use-after-free on the unchanged revision and pass Miri with the patch. The GC and engine tests pass. The measured cost is substantial: median collection time is **3.54× baseline** on the workload below.

Deliverable: [boa_gc_finalizer.patch](boa_gc_finalizer.patch). It includes five regression tests and applies cleanly to the baseline (`git apply --check`). [baseline](baseline) is an unchanged worktree; the original Cargo checkout and supplied reproducer sources were not edited. Nothing was filed upstream or sent to maintainers; no files under `/ssd1/sichangheagent/email` were written.

## Implementation

The requested rule is “fresh second mark from post-finalizer roots.” The [model report](../vlm3_review/job1/REPORT.md), section “Not done, and why,” explicitly says: “I did not model `ref_count`, `non_root_count`, `Gc::finalize` decrementing, or `DropGuard`.” The real implementation therefore also needs reference-count maintenance:

- `Gc` and `Ephemeron` finalization no longer decrement counts for handles that still exist. Ordinary handle destruction decrements them.
- After callbacks, reset marks and internal-handle counts, recount all heap handles, and mark from the resulting roots.
- Repeat finalization and fresh marking if callbacks make additional objects unreachable. A set records strong objects already finalized during this collection. Pending ephemeron contents are cleared, including when an externally held ephemeron's key becomes unreachable.
- Before deallocation, recount handles in dead allocations and subtract those counts from their targets. All targets still exist at this point. This accounts for handle destruction suppressed by `DropGuard` without touching freed targets.

The additional rounds matter: otherwise a finalizer that removes a root can cause an initially live object to be swept without finalization, or leave a surviving weak handle pointing at a freed key. The new `finalizer_drops_rooted_key` test checks both outcomes. The other tests cover cloning a child, resurrecting a cycle, moving a child into an already-marked object, and publishing a weak handle. Repeated collections and eventual empty-heap assertions check survivor reference counts as well as immediate access.

Control flow and assumptions: [DESIGN.md](DESIGN.md). This is a source implementation validated by tests, not a new formal proof of the collector.

## Validation

Run `bash validate.sh` from this directory. Its final run exited 0. It checks the expected baseline failures, patched reproducers, both default-feature test suites, GC tests under Miri, Clippy with warnings denied, formatting, and diff whitespace. Commands and logs are retained locally.

Both [original-repro baseline](miri-original-repro-baseline.log) and [main-repro baseline](miri-main-repro-baseline.log) exited 1 with this exact diagnostic:

```text
error: Undefined Behavior: constructing invalid value of type &boa_gc::GcBox<Child>: encountered a dangling reference (use-after-free)
```

Both [original-repro fixed](miri-original-repro-fixed.log) and [main-repro fixed](miri-main-repro-fixed.log) exited 0 and printed:

```text
child.v=0xc0ffee
```

The manifests in `repro-baseline/` and `repro-fixed/` compile the supplied files directly from `../vlm2_boagc/repro/src/main.rs` and `../vlm2_boagc/r_main/src/main.rs`. Only their dependency paths differ.

[tests.log](tests.log) records these result lines for GC unit tests, engine unit tests, and engine doctests, respectively:

```text
test result: ok. 35 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.28s
test result: ok. 1139 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.30s
test result: ok. 185 passed; 0 failed; 3 ignored; 0 measured; 0 filtered out; finished in 0.19s
```

The four engine integration-test targets also passed: 1, 2, 1, and 7 tests. This is `cargo test -p boa_gc -p boa_engine`, not the separate Test262 suite or all feature combinations.

[miri-gc-tests.log](miri-gc-tests.log) records:

```text
test result: ok. 34 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 7.61s
```

The existing million-node recursion test is explicitly ignored under Miri. Isolation is disabled for the suite because its existing file test opens a file. The standalone reproducer runs keep default isolation. [clippy.log](clippy.log) ends with `Finished` and no diagnostics under `-D warnings`; [fmt.log](fmt.log) is empty.

Tool versions: `rustc 1.97.1 (8bab26f4f 2026-07-14)` and `miri 0.1.0 (8d1a764304 2026-10-06)`, on Linux x86_64, AMD EPYC 7763.

## GC cost

[bench.rs](bench.rs) retains a chain of 4,096 nodes. Each of 1,000 iterations allocates and drops another 4,096-node chain pointing into it, then forces collection. These heaps stay below the initial automatic-collection threshold. The nodes have derived, empty finalizers; timing therefore measures collector work rather than user callback work. `gc_ms` sums only forced-collection durations; `total_ms` includes allocation and collection, excluding initial live-chain construction and final teardown.

Run `bash benchmark.sh`. Both binaries use the same source, Rust compiler, release optimization, fat LTO, and one codegen unit. The script pins them to CPU 2, warms each once, then runs nine samples per version in alternating order. This is a shared host, not a controlled performance lab.

| Time per 1,000 collections | Baseline median | Patched median |
| --- | ---: | ---: |
| Collection only | 110.984 ms | 392.697 ms |
| Allocation + collection | 144.988 ms | 467.860 ms |

Calculated from [benchmark.log](benchmark.log): collection time increases 253.8% (3.54×); total time increases 222.7% (3.23×). Collection ranges are 109.984–116.422 ms before and 387.741–416.866 ms after. These medians are computed from nine samples; representative raw records are:

```text
baseline round=9 collections=1000 live_nodes=4096 dead_nodes_per_collection=4096 gc_ms=110.984 total_ms=144.988
fixed round=4 collections=1000 live_nodes=4096 dead_nodes_per_collection=4096 gc_ms=392.697 total_ms=467.860
```

The added full tracing, dead-handle accounting, and finalized-object set are plausible contributors; their individual costs were not profiled. This result does not establish an engine-wide slowdown or cost for other heap shapes.

## Review and remaining limits

A context-free reviewer (`/root/reviewer`) identified the newly dead object and weak-key cases during initial review. After the loop and regression were added, the reviewer reported: “No remaining material correctness findings from focused code inspection.” The reviewer did not run tests; the runs above are this task's validation.

The reviewer also noted: “callbacks that repeatedly refill pending ephemerons could prevent convergence.” This is an untested termination risk. The patch does not establish termination for arbitrary callbacks, correctness of arbitrary unsafe `Trace` implementations, or safety of arbitrary custom destructors. It does remove the demonstrated use-after-free and the two identified fresh-mark regressions in the exercised cases.

Process lesson: the original reachability model correctly identified the marking rule, but implementing it required checking reference counts and finalization of objects that become unreachable during callbacks. Keeping those boundaries explicit made the additional regressions testable.

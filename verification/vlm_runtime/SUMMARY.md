# vlm_runtime summary
(authored by agents unless marked 🧑)

Per-substrate reports: dynstate/REPORT.md, tabiso/REPORT.md, lightpanda/REPORT.md (each has run instructions, fact/belief labels).

## runtime verification with dynamic state (dynstate/)
- built: fail-closed Z3 binary64 executor over a restricted JS subset; conditional properties: no exception, no document.cookie read, each while invocation ≤8 iterations; environment contract in dynstate/REPORT.md
- corrected rerun: state-agnostic mode → INCONCLUSIVE; good snapshot → all three checks pass under the contract; bad snapshot → cookie read only (out-of-range indexing yields undefined, then NaN); roughly 200 ms including parsing; evidence in ../cx_dynstate/REPORT.md
- blockers: full JS semantics (eval, prototypes, async); proof only valid while depended-on state unchanged → needs guard (not built); real scripts unmeasured
- differentiator (belief, prior work unchecked online): "snapshot as precondition + proof + guard" at page load vs trace monitors (Jalangi/ExpoSE) and state-agnostic analyzers (TAJS/SAFE)

## same-process tab isolation (tabiso/)
- fact: per-tab memory at N=50, Node 22: vm context 0.44 MB, worker isolate 0.78 MB, process 9.0 MB → ~20x
- inference: Chrome's ~300 MB/tab is mostly DOM/layout/GPU, so engine-only sharing saves little; claim needs whole renderer in one process
- built: Rust two-realm heap model w/ write barrier + shared-immutable space; random testing 20000 runs: 0 invariant breaks w/ barrier, 19975 w/o (testing, not proof)
- blockers: Spectre/side channels; C++ engines vs Rust verifiers; JIT output needs per-run checking; CVE IDs listed from memory, unverified

## Lightpanda (lightpanda/)
- fact: nightly 1.1.0 run on 14 localhost pages vs Chrome 150: all terminate; 8 DOM/JS-state match; 6 differ (resource loading, layout estimation, e.g. display:contents width 5 vs 29.09, same family as WEB_FAILURE_TARGETS #1)
- fact: egress monitor: --block-urls blocked forbidden origin except a WebSocket upgrade → possible filter gap (1 build, 1 pattern; not reported upstream)
- fact: ~290k LoC Zig + V8; no Zig verifier found; source not built (needs Zig 0.17)
- belief: verifiable pieces: URL, MIME, cookies, CSS selector parsing, request filter; crawler threat model (egress, termination, state fidelity) narrow and checkable

## next (agent recommendation)
- dynstate: real CDP snapshots + mutation-observer guard; literature check for novelty
- tabiso: port model to Kani/Verus; try QuickJS
- lightpanda: WPT subset diff; confirm WebSocket/redirect --block-urls gap

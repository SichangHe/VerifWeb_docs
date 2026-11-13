# Boa maintainer triage
(authored by agents unless marked 🧑)

Judgment: likely accepted as a real soundness bug. Main reproduces it, and the collector's own docs say finalizers may resurrect nodes, so there is no apparent not-a-bug basis. Maintainers may rate it low priority because no engine path is shown. The draft needs a main-run result and clearer scope. This is my triage assessment, not a maintainer decision.

Reviewed [the draft](../vlm4_drafts/boa_gc_finalizer_uaf.md) without changing it. Fresh work directories: [gc/](gc/) (boa_gc 0.21.0) and [gcmain/](gcmain/) (path dependency on current main). Upstream `main` resolved (`git ls-remote`) to `329e89748ed34e218fe593b4209b1dbe1d6eb64d` on 2026-11-04; it matches the retained clone `boa/upstream`.

## Execution evidence

Used the draft's `Cargo.toml` and `main.rs` unchanged, with rustc 1.97.1 nightly Miri:

- [boa_gc =0.21.0, Miri](gc/miri-021.log): Undefined Behavior, "dangling reference (use-after-free)", frames `gc.rs:316`, `gc.rs:363`, `main.rs:24`. Matches the draft.
- [Current main via path dependency, Miri](gcmain/miri-main.log): same error, same frames (`gc.rs:316:18`, `gc.rs:363:9`). The draft says it did not run main; it reproduces there.
- Native `cargo run` on main prints `child.v=0xc0ffee` (silent read of freed memory), as the draft says.
- Not run: 0.22.0 and 0.21.1.

## Current upstream source evidence

- [`Collector::collect`](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/gc/src/lib.rs#L226-L245): `trace_non_roots` (L228), first `mark_heap` (L232), `finalize` (L240), second `mark_heap` (L243-244). The draft's line numbers match.
- [`impl Finalize for Gc`](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/gc/src/pointers/gc.rs#L320-L326): `self.inner_ptr.as_ref().dec_ref_count();`.
- [`is_rooted`](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/gc/src/internals/gc_header.rs#L108-L110): `self.non_root_count() < self.ref_count()`.
- Design intent, [lib.rs L215](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/gc/src/lib.rs#L215): "3. Mark again because `Finalize::finalize` can potentially resurrect dead nodes." The collector claims to support resurrection, so the UAF contradicts stated intent.
- [`Finalize`](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/gc/src/trace.rs#L63-L67) has no doc forbidding stored handles; the `Trace` safety text covers only incorrect `Trace` impls. This supports the draft's "safe trait" claim, though a maintainer could still argue an implicit contract.
- [SECURITY.md](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/SECURITY.md): "If you find any potential vulnerability, join our [Matrix](https://matrix.to/#/#boa:matrix.org) space". The draft's channel note matches. Supported: "the latest 0.x release and the current `main` branch".
- Template `.github/ISSUE_TEMPLATE/bug_report.md` exists (fields not checked).
- Not checked: duplicates (#5567, #5187) and rust-gc #124; no issue search was done.

## Concrete draft changes, in priority order

1. Original: "I did not re-run Miri on main for this report." Replace with: "Also reproduced under Miri with `boa_gc = { git = "https://github.com/boa-dev/boa", rev = "329e89748ed34e218fe593b4209b1dbe1d6eb64d" }`: same error, frames gc.rs:316 / :363." Update Build environment ("source read only") likewise.
2. Original: "the causal chain is my analysis" / "an escaped handle may not make the child look rooted". The mechanism is unverified; no instrumentation was run. Keep the hedge, or add a debug print of `non_root_count`/`ref_count` before the second mark.
3. Original: "Same Miri error and same frames (gc.rs:316 / :363) with `boa_gc = "=0.22.0"`." Not re-run here; keep only if the author's run is recorded, and give the one-line Cargo.toml change.
4. Original: "Whether JS running on boa_engine can trigger it is unknown; I infer probably not". Maintainers will ask this first. Add the command and result of a search of `core/engine` for `Finalize` impls that store `Gc`, or label it unchecked. State severity: soundness bug in the safe public `boa_gc` API.
5. Original: "Possible direction (untested; ...)". Add the lib.rs L215 quote as evidence that resurrection is meant to be supported.
6. Original: "(Same class as rust-gc issue #124, ...)". Add the link; unverified here.

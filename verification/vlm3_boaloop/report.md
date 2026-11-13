# vlm3_boaloop: independent check of the Boa event-loop claim

(authored by agents unless marked 🧑)

Checked claim: `out/cloud/p2_event_loop.md` (cloud report). Everything below was re-run here on Boa commit `329e89748ed34e218fe593b4209b1dbe1d6eb64d` (2026-10-31). Cloud bundle was copied to `bundle/` before use; Boa clone in `src/boa`, patched worktree in `src/boa_patched`, all re-run outputs in `rerun/`.

## Verdict

The claim holds. Every number I could re-run matched except the CLI failure count (10 per run here vs 123–159 in the cloud), which is consistent with the cloud's "flaky, timing-dependent" description.

## 1. Own minimal repro (fact)

Harness `src/boa/examples/src/bin/vlm3_repro.rs` (written by me, not the bundle): `Context::default()` + `boa_runtime::register(ConsoleExtension::default(), None, ..)` + `eval` + `run_jobs()`. Output, identical over 5 runs (same md5):

- `setTimeout(T0,0); P.then(P1)` → `T0,P1` (HTML: `P1,T0`)
- `queueMicrotask(M1); setTimeout(T0,0)` → `T0,M1` (HTML: `M1,T0`)
- `P.then(()=>{P0; setTimeout(T1,0); P.then(P2)})` → `P0,T1,P2` (HTML: `P0,P2,T1`)
- `setTimeout(()=>{T0; P.then(P1)},0); setTimeout(T2,0)` → `T0,T2,P1` (HTML: `T0,P1,T2`)

With the cloud patch applied, the same binary prints the HTML order for all four.

Cause in source (`core/engine/src/job.rs`, `SimpleJobExecutor::run_jobs_async`):
- https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/job.rs#L970 — `// Dispatch all past-due timeout jobs before the termination check.` then runs every due timer back to back
- https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/job.rs#L1028 — `let jobs = mem::take(&mut *self.promise_jobs.borrow_mut());` (snapshot; jobs enqueued during it wait for the next iteration, i.e. after timers)

## 2. Bug or intended? (fact, then inference)

What Boa says:
- `job.rs` L863–866: "A simple FIFO executor that bails on the first error. … This is the default job executor for the [`Context`], but it is mostly pretty limited for a custom event loop."
- `job.rs` L18–19 (module doc): "[`SimpleJobExecutor`], which is a simple FIFO queue that runs all jobs to completion, bailing on the first error encountered."
- `core/wintertc/src/timers/mod.rs` L1–3 (the setTimeout implementation): "TC55 timer APIs: `setTimeout`, `clearTimeout`, `setInterval`, `clearInterval`. … Spec: <https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html#timers>"
- `ABOUT.md` L23: "[**`boa_wintertc`**] - Boa's `WinterTC` (TC55) Minimum Common Web API implementation."
- `cli/src/executor.rs` L69–70: "Continually run all pending promise jobs, yielding to the async executor after every successful run." (no ordering claim)

Inference: no Boa text promises HTML microtask-checkpoint ordering for the executor, and it calls itself "limited". But the timers that feed it cite the HTML timers spec as their spec, and are registered by default. So: not a documented guarantee being broken, but a spec-conformance bug relative to the spec Boa itself cites. Whether maintainers would call it a bug is unknown (opinion: likely yes; #5308 below shows they compare against Node's timer behaviour).

## 3. Existing reports (fact; `gh` CLI search, 2026-11-04)

No issue/PR about promise-vs-timer ordering found. Searched issues for "setTimeout", "queueMicrotask", "microtask", "event loop", "ordering", and PRs for "SimpleJobExecutor". Related but different (timers lost/starved/IDs, not ordering): #4782 "timeout jobs scheduled for `now` can be skipped", #5308 "cli/src/executor.rs starvation bug with setTimeout(..., 0)", #4706, #4730, #4886, #5378, tracking issue #4988 (WinterTC gap analysis; lists `queueMicrotask` and timers as done, nothing on ordering). Absence is a belief, limited to these keywords.

## 4. Cloud bundle re-run (fact)

Conformance (bundle's `run.py`/`model.py`, paths rewritten, ≤4 callbacks, depth ≤4, 9,430 programs), es2019 failures:
- Node v22.21.1 (model sanity check): 0 — same as cloud
- Boa SimpleJobExecutor original: 4,171 — same as cloud
- Boa SimpleJobExecutor + patch: 0 — same as cloud
- Boa CLI: 10, 10, 10 in 3 runs, with different program sets each run (so nondeterministic); cloud got 123–159. Host load avg ~40–70 on 128 cores. Observed CLI failures include timer batching (`T0,T1,T3,P2`, expected `T0,T1,P2,T3`) and timer reordering (`T0,T1,T3,T2`, expected `T0,T1,T2,T3`), the latter a class the cloud report did not name

Patch (`bundle/simplejobexecutor-fix.diff`, needed `git apply --directory=core`; applied form in `patch_as_applied.diff`): `cargo test -p boa_engine --lib job` 2 passed; `cargo test -p boa_wintertc` 54 + 1 passed — same as cloud. Full test suite/test262 not run (cloud didn't either).

TLC (tla2tools v1.7.4): html_8 no error, 4,082 distinct states; boa_fixed_8 no error, 12,598; node10_8 and boa_simple_5/8 violate `NoTaskWithPendingMicrotasks` — all same as cloud.

Verus: 0.2026.10.26.d17fbd0 with z3 4.15.4 and `-V no-solver-version-check` (cloud used 0.2026.11.04 / matching z3; no newer build runs on this host's glibc). Patched: "10 verified, 0 errors"; original: "13 verified, 1 errors", the error at `q.run_timer()` back-to-back loop — same as cloud.

## Limits

- TLA+/Verus models are hand abstractions; I did not audit their fidelity to `job.rs` beyond confirming the real binary shows the same bug.
- I did a `git fetch` in `/ssd1/sichangheagent/verus` (shared checkout) to read its upstream version; only remote refs changed.

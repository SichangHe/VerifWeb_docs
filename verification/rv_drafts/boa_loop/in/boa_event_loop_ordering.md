# DRAFT, NOT FILED. Template: boa-dev/boa `.github/ISSUE_TEMPLATE/bug_report.md` (type: Bug)
(authored by agents unless marked 🧑)

**Title:** `SimpleJobExecutor` runs due timers before promise jobs enqueued by earlier jobs (differs from HTML event-loop ordering)

**Describe the bug**

With the default `Context` (`SimpleJobExecutor`), a promise reaction / `queueMicrotask` callback can run after a `setTimeout(..., 0)` callback that was scheduled earlier or at the same time. In HTML (and Node >= 11, Chromium), all microtasks run to completion after each task, before the next timer task. Boa's timers cite the HTML timers spec (`core/wintertc/src/timers/mod.rs` L1-3), so this looks like a mismatch with the cited spec. `SimpleJobExecutor` documents itself as "mostly pretty limited" (`job.rs` L863-866), so maintainers may consider it intended; I do not know.

Cause (by source reading, commit below), in `SimpleJobExecutor::run_jobs_async`:
- All past-due clock jobs are dispatched back to back, with no promise-job draining between them.
- Promise jobs are taken as a snapshot (`mem::take(&mut *self.promise_jobs.borrow_mut())`); jobs enqueued while it runs wait for the next loop iteration, i.e. after the timers.

**To Reproduce**

Checkout boa `329e89748ed34e218fe593b4209b1dbe1d6eb64d`. Add `examples/src/bin/order_repro.rs`:

```rust
use boa_engine::{Context, Source};
use boa_runtime::extensions::ConsoleExtension;
fn main() {
    let progs = [
        r#"const P=Promise.resolve(); setTimeout(()=>console.log("T0"),0); P.then(()=>console.log("P1"));"#,
        r#"const P=Promise.resolve(); P.then(()=>{console.log("P0"); setTimeout(()=>console.log("T1"),0); P.then(()=>console.log("P2"))});"#,
        r#"const P=Promise.resolve(); setTimeout(()=>{console.log("T0");P.then(()=>console.log("P1"))},0); setTimeout(()=>console.log("T2"),0);"#,
        r#"queueMicrotask(()=>console.log("M1")); setTimeout(()=>console.log("T0"),0);"#,
    ];
    for p in progs {
        println!("== {p}");
        let mut ctx = Context::default();
        boa_runtime::register(ConsoleExtension::default(), None, &mut ctx).unwrap();
        ctx.eval(Source::from_bytes(p)).unwrap();
        ctx.run_jobs().unwrap();
    }
}
```

Run `cargo run --release -p boa_examples --bin order_repro`.

**Expected behavior**

Per HTML "perform a microtask checkpoint" after each task (Node 22.21.1 gives these too, and the 9,430-program comparison below):

| program | expected | Boa actual |
|---|---|---|
| 1 | `P1, T0` | `T0, P1` |
| 2 | `P0, P2, T1` | `P0, T1, P2` |
| 3 | `T0, P1, T2` | `T0, T2, P1` |
| 4 | `M1, T0` | `T0, M1` |

Re-run on 2026-11-04 on the unmodified commit: actual output was exactly the "Boa actual" column (printed in the order `T0 P1 | P0 T1 P2 | T0 T2 P1 | T0 M1`). It was identical over 5 earlier runs.

Wider check (confirmed by independent rerun): a generated corpus of 9,430 programs (<= 4 grammar nodes, depth <= 4, mixing timers, `.then` chains, `await`, `queueMicrotask`), compared against Node 22 with the ES2019 await semantics: SimpleJobExecutor fails 4,171; with the earlier version of the patch (before the cancellation fix below), 0 fail. The corpus was not re-run against the final patch. (The corpus is a finite grammar, not arbitrary JS. The generator is not included; it can be shared.)

**Build environment**

- OS: Linux 5.15.0-202-generic (Ubuntu-style kernel), x86_64
- Target triple: x86_64-unknown-linux-gnu
- Rustc: rustc 1.97.1 (8bab26f4f 2026-07-14)
- Boa: commit `329e89748ed34e218fe593b4209b1dbe1d6eb64d` (2026-10-31)

**Additional context**

- Not covered here: `boa_cli`'s own executor (`cli/src/executor.rs`) also shows ordering mismatches (9 of 9,430 in one rerun, timing dependent, nondeterministic); I did not analyze them further.
- Possibly related but different symptoms: #4782, #5308, #4706. I searched issues/PRs for setTimeout / queueMicrotask / microtask / event loop / ordering / SimpleJobExecutor and found no report of this ordering; that search is keyword-limited.
- Proposed patch (attached as `boa_event_loop_ordering.patch`, against `core/engine/src/job.rs`): a `drain_promise_jobs` helper that runs promise jobs until the queue is empty, called before due timers, after each timeout/interval callback, and in place of the snapshot. It checks the cancellation token inside the drain and abandons the remaining timers/jobs when set, so `get_cancellation_token()` still stops an endless promise chain. Limits: it drains only promise jobs; it does not implement the full HTML checkpoint (reentrancy guard, rejection notification), `clear_kept_objects` still runs once per outer iteration, and generic jobs stay snapshot-based. Interval/nonzero-delay timer semantics were not tested.
- Patch testing: the ordering repro prints the expected order for all 4 programs; `cancel_stop` (a promise job that re-enqueues itself forever, token set after 20 ms) returns instead of hanging; test results below.

Final-patch results (debug build, rustc 1.97.1, 2026-11-04): ordering repro prints the expected order for all 4 programs; `cancel_stop` prints `cancelled` and exits 0 (the earlier patch version hung; `timeout 3` exit 124); `cargo test -p boa_engine --lib job`: 2 passed; `cargo test -p boa_wintertc`: 54 passed + 1 doctest passed. Full test suite and test262 not run. `cancel_stop` source: (attach `examples/src/bin/cancel_stop.rs`: `SimpleJobExecutor` as the context's executor, eval `function again(){Promise.resolve().then(again)} again();`, set the token from another thread after 20 ms, call `run_jobs()`). Not verified on the unpatched commit that `cancel_stop` returns (the original-library build timed out in review), though source inspection says the snapshot loop checks the token each iteration.

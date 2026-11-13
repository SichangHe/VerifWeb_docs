(authored by agents unless marked 🧑)

Boa `SECURITY.md`: "If you find any potential vulnerability, join our [Matrix](https://matrix.to/#/#boa:matrix.org) space and contact anyone who is an admin."

**Title:** `SimpleJobExecutor` runs due timers before promise jobs enqueued by earlier jobs (differs from HTML event-loop ordering)

**Describe the bug**

With the default `Context` (`SimpleJobExecutor`), a promise reaction / `queueMicrotask` callback can run after a `setTimeout(..., 0)` callback that was scheduled earlier or at the same time. In HTML (and Node >= 11), all microtasks run to completion after each task, before the next timer task: the event loop's processing model ends each task with "perform a microtask checkpoint" (<https://html.spec.whatwg.org/multipage/webappapis.html#perform-a-microtask-checkpoint>). Boa's timers cite the HTML timers spec ([`core/wintertc/src/timers/mod.rs` L3](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/wintertc/src/timers/mod.rs#L3)), so this looks like a mismatch with the cited spec. The [`SimpleJobExecutor` docs (`job.rs` L865)](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/job.rs#L865) say: "This is the default job executor for the [`Context`], but it is mostly pretty limited for a custom event loop."

Question for maintainers: is ordering parity with HTML in scope for the default `SimpleJobExecutor`, or only for custom executors? If the latter, I'd suggest documenting the difference.

Cause (by source reading, commit below), in [`SimpleJobExecutor::run_jobs_async` (`job.rs` L955-L985)](https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/job.rs#L955-L985):
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

Per HTML "perform a microtask checkpoint" after each task (Node 22.21.1 gives these too):

| program | expected | Boa actual |
|---|---|---|
| 1 | `P1, T0` | `T0, P1` |
| 2 | `P0, P2, T1` | `P0, T1, P2` |
| 3 | `T0, P1, T2` | `T0, T2, P1` |
| 4 | `M1, T0` | `T0, M1` |

Running the repro on the unmodified commit prints exactly the "Boa actual" column (`T0 P1 | P0 T1 P2 | T0 T2 P1 | T0 M1`).

**Build environment**

- OS: Linux 5.15.0-202-generic (Ubuntu-style kernel), x86_64
- Target triple: x86_64-unknown-linux-gnu
- Rustc: rustc 1.97.1 (8bab26f4f 2026-07-14)
- Boa: commit `329e89748ed34e218fe593b4209b1dbe1d6eb64d` (2026-10-31)

**Additional context**

- Possibly related but different symptoms: #4782 (closed as not planned, so maintainers have declined a `SimpleJobExecutor` timer fix before), #4785 (merged, "Fix due-now timeout jobs in executor and CLI"), #4730 (due-now timeout dropped; PR, closed, not merged), #4926, #5308, #4706. Status as of 2026-11-04. Keyword search of issues/PRs (setTimeout, queueMicrotask, microtask, event loop, ordering, SimpleJobExecutor, checkpoint) found no report of this ordering; that search is keyword-limited.
- I can open a PR with a regression test (promise-then vs `setTimeout` ordering, plus the cancel case) if the direction is acceptable.
- Proposed patch (attached as `boa_event_loop_ordering.patch`, against `core/engine/src/job.rs`; applies cleanly to the commit above): a `drain_promise_jobs` helper that runs promise jobs until the queue is empty, called before due timers, after each timeout/interval callback, and in place of the snapshot. It checks the cancellation token inside the drain, so `get_cancellation_token()` still stops an endless promise chain.
- Patch limits: drains only promise jobs, not the full HTML checkpoint (no reentrancy guard, no rejection notification); generic jobs stay snapshot-based; interval/nonzero-delay timer semantics were not tested.
- Patch testing (debug build, rustc 1.97.1, 2026-11-04): the ordering repro prints the expected order for all 4 programs; `cargo test -p boa_engine --lib job`: 2 passed; `cargo test -p boa_wintertc`: 54 passed + 1 doctest passed. The full test suite and test262 were not run.
- `cancel_stop` is a regression guard for the patch, not a second bug (a promise job re-enqueues itself forever; the token is set from another thread after 20 ms): returns and prints `cancelled`, exit 0, on both the patched and the unpatched commit (release build). Source:

```rust
use boa_engine::{Context, Source, job::SimpleJobExecutor};
use std::{rc::Rc, sync::atomic::Ordering, time::Duration};

fn main() {
    let executor = Rc::new(SimpleJobExecutor::new());
    let stop = executor.get_cancellation_token();
    let mut context = Context::builder().job_executor(executor).build().expect("context");
    context.eval(Source::from_bytes("function again(){Promise.resolve().then(again)} again();")).expect("eval");
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(20));
        stop.store(true, Ordering::Relaxed);
    });
    context.run_jobs().expect("jobs");
    println!("cancelled");
}
```

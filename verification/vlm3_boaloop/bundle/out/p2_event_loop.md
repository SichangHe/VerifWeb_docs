# p2_event_loop: model-checking JS event-loop ordering against the HTML/ECMAScript spec

Authored by agents (Claude Code cloud session), 2026-11-04. No 🧑 content.
Labels used: **[fact]** = observed by running code here or quoted from a source; **[inference]** = my reasoning from facts; **[opinion]** = judgment.

## 1. Bottom line

- **[fact]** I built three checkers for the same property, "a macrotask never starts while a microtask is pending, and microtasks run FIFO":
  - an executable reference model, plus bounded exhaustive differential testing of real binaries (all 9,430 programs of a small grammar);
  - a TLA+ spec checked with TLC;
  - a Verus proof of the scheduling core.
- **[fact]** The check catches both real historical bugs I targeted:
  - Node ≤10 ran all expired timers before draining microtasks (nodejs/node#22257, fixed in Node 11);
  - Node 8's `await` took 1 tick where the 2018 spec required 3 (V8 blog).
- **[fact] New finding: Boa's default event loop violates HTML ordering.** At Boa commit `329e8974` (2026-10-31), `SimpleJobExecutor`, which `Context::default()` uses, fails 4,171 of 9,430 programs, deterministically. The simplest failing program is `setTimeout(()=>log("T0"),0); P.then(()=>log("P1"))`: the spec order is `P1,T0`; Boa prints `T0,P1`.
- **[fact]** A 36-line patch to `SimpleJobExecutor` fixes all 4,171 failures:
  - the patched build fails 0 of 9,430;
  - the patched loop is verified in Verus (10 obligations, 0 errors) and model-checked in TLA+;
  - Boa's own `job` and `boa_wintertc` tests still pass.
- **[fact]** The Boa CLI's separate event loop also fails, flakily: 123–159 of 9,430 failures per run. These are timer batching like Node ≤10, and microtasks being overtaken by timers.
- **[fact]** Nothing was filed upstream. I found no existing Boa issue about this (see §5).

## 2. The property (spec basis, verbatim)

HTML Living Standard, event loop processing model (https://html.spec.whatwg.org/multipage/webappapis.html#event-loop-processing-model). After running one task:
> "Set the event loop's currently running task to oldestTask. / Perform oldestTask's steps. / Set the event loop's currently running task back to null. / Perform a microtask checkpoint."

Perform a microtask checkpoint (https://html.spec.whatwg.org/multipage/webappapis.html#perform-a-microtask-checkpoint):
> "3. While the event loop's microtask queue is not empty: 1. Let oldestMicrotask be the result of dequeuing from the event loop's microtask queue. […] 3. Run oldestMicrotask."

Timer order (https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html#run-steps-after-a-timeout):
> "Wait until any invocations of this algorithm that had the same global and orderingIdentifier, that started before this one, and whose milliseconds is less than or equal to this one's, have completed."

ECMA-262 HostEnqueuePromiseJob (https://tc39.es/ecma262/#sec-hostenqueuepromisejob):
> "Jobs must run in the same order as the HostEnqueuePromiseJob invocations that scheduled them."

`await` semantics changed in tc39/ecma262#1250 (https://github.com/tc39/ecma262/pull/1250), "Normative: Reduce the number of ticks in async/await", merged 2019-02-26:
> "because `await` always wraps a Promise with another Promise, there are three job queue items enqueued and dequeued before calling `f` in the `await` example, whereas there is just a single item for the `then` usage. […] This patch changes the semantics of await to reduce the number of job queue turns that are taken in the common `await` Promise case by replacing the unconditional wrapping with a call to PromiseResolve."

So the model takes a parameter: `es2017` gives `await P` = 3 jobs, `es2019` gives 1 job.

## 3. What was built

### 3a. Executable reference model + bounded exhaustive conformance (the main checker)

- **Grammar.** A program is a forest of callbacks, and each callback logs a unique label. Node kinds:
  - `T` = `setTimeout(cb,0)`
  - `M` = `queueMicrotask(cb)`
  - `P` = `P.then(cb)`, where `P = Promise.resolve()`
  - `C` = `P.then(cb).then(()=>log(x'))`
  - `A` = `(async()=>{await P; cb})()`
- **Bound.** At most 4 callbacks, nesting depth ≤4, which gives 9,430 programs. A smaller run (≤3 callbacks, 680 programs) was used first.
- **Model.** About 40 lines of Python (Appendix A). It has one FIFO task queue and one FIFO microtask queue, and drains microtasks to empty after the script and after every task.
- **Validation of the model itself.** **[fact]** Chromium (Playwright build in this container) matches the `es2019` model on 680/680 programs. It also matches on all 9,430 (§4). Node 12 and Node 22 match on 9,430/9,430.
- **Engines run.** Each program runs in a fresh process or Context:
  - Node 8.17.0, 10.24.1, 11.0.0, 12.0.0, 22.23.4;
  - Boa CLI (`target/release/boa`);
  - Boa `SimpleJobExecutor`, via a 25-line harness (Appendix D) that uses `Context::default()` + `boa_runtime::register` (console, setTimeout, queueMicrotask);
  - the same harness with my patch;
  - Chromium.
- `queueMicrotask` is polyfilled as `Promise.resolve().then(f)` only where it is missing (Node 8/10). **[inference]** Ordering is identical, since both enqueue one job immediately.

### 3b. TLA+ (Appendix B)

- **State.** An abstract loop with one microtask queue and one timer queue. Each job nondeterministically spawns ≤2 new jobs (`M` or `T`), within a global `Budget`.
- **Variants.** Four schedulers: `html`, `node10` (run all expired timers, then drain), `boa_simple` (original Boa loop, including the `mem::take` snapshot), and `boa_fixed` (patched).
- **Invariants.** `NoTaskWithPendingMicrotasks`, `MicroFIFO`, `TaskFIFO`.

### 3c. Verus (Appendix C)

- **Model.** The Boa scheduling core is rewritten as executable Rust over `Vec`+head-index queues.
- **Unknown JS behaviour.** Running a JS callback is an `external_body` oracle that may enqueue anything.
- **Property.** `run_timer` has precondition `micro_empty()`, so Verus must prove that every call site has drained the microtask queue. A ghost sequence proves microtask FIFO.

## 4. Results

### Conformance, 9,430 programs (failures / total)

Against the es2019 model (current spec):
- Chromium: 0 (the model agrees with Chromium on 9,430/9,430)
- Node 22.23.4: 0
- Node 12.0.0: 0
- Node 11.0.0: 2,934. **[fact]** All of these are `await` tick-count differences: Node 11 matches es2017 with 0 failures.
- Node 10.24.1: 3,068, i.e. the es2017 await gap plus 138 timer-batching failures. Against es2017 it fails 138, all of which contain ≥2 `setTimeout`.
- Node 8.17.0: 140, all of which contain ≥2 `setTimeout` (timer batching). Against es2017 it fails 3,069: the await bug.
- Boa `SimpleJobExecutor`, original: 4,171, deterministic (8/8 identical reruns at the 680 bound)
- Boa `SimpleJobExecutor`, patched: **0**
- Boa CLI: 159 in the main run; 129, 123, 124, 146, 137 in 5 reruns. These ran under CPU load from other jobs. **[inference]** The failures are timing-dependent.

### TLC (Budget = 5 and 8, every reachable state explored where no error)

- `html`: no error; 4,082 distinct states at Budget 8.
- `boa_fixed`: no error; 12,598 distinct states at Budget 8.
- `node10`: `NoTaskWithPendingMicrotasks` violated. Counterexample: script queues timers 1,2 → timer 1 runs and queues microtask 3 → timer 2 starts while 3 is pending.
- `boa_simple`: violated at depth 3. Counterexample: script queues timer 1 and microtask 2 → the loop dispatches due timers first → timer 1 starts while 2 is pending.

### Verus 0.2026.11.04.d804d56 (rustc 1.99.1)

- Patched loop: `verification results:: 10 verified, 0 errors`.
- Original loop structure, same `Q` methods: `verification results:: 13 verified, 1 errors`. The single error is `precondition not satisfied` at `{ q.run_timer(); }`, the back-to-back timer loop. This is the bug.
- Caveat: the proof is partial correctness only, since JS can loop forever (`exec_allows_no_decreases_clause`).

## 5. Real bugs and how the check catches them

### Bug 1: Node ≤10 timer batching

nodejs/node#22257 (https://github.com/nodejs/node/issues/22257), "MacroTask and MicroTask execution order", 2018-08-10, Node 10.8.0:
> "Currently there is a different in the execution order of Macro and Micro tasks between browsers and NodeJS"

Its repro has two `setTimeout` callbacks that each start a promise chain:
- expected ("Chrome / Edge / Safari / Firefox"): `Timeout 0, Promise 1 0, Promise 2 0, Timeout 1, Promise 1 1, Promise 2 1`;
- observed ("Node"): `Timeout 0, Timeout 1, Promise 1 0, Promise 2 0, Promise 1 1, Promise 2 1`.

The fix, nodejs/node#22842 (https://github.com/nodejs/node/pull/22842), commit message:
> "In order to better match the browser behaviour, run nextTicks (and subsequently the microtask queue) after each individual Timer and Immediate, rather than after the whole list is processed."

Node 11.0.0 changelog (https://github.com/nodejs/node/blob/main/doc/changelogs/CHANGELOG_V11.md#11.0.0):
> "`nextTick` queue will be run after each immediate and timer. [#22842]"

**[fact]** The checker's smallest counterexample on Node 10 is the 3-callback analogue of #22257:
```
setTimeout(()=>{log("T0");P.then(()=>log("P1"))},0); setTimeout(()=>log("T2"),0);
expected T0,P1,T2   node10 got T0,T2,P1
```
- Node 11 fails 0 of 9,430 under es2017, which matches the fix landing in 11.0.0.
- TLC finds the same shape abstractly in 4 states.

### Bug 2: Node 8 `await` skipped ticks

V8 blog "Faster async functions and promises" (https://v8.dev/blog/fast-async), 2018-11-12:
> "there was a handy bug in Node.js 8 that caused `await` to skip microticks in some cases, resulting in better performance. The bug started out as an unintended spec violation, but it later gave us the idea for an optimization."

> "Although this behavior seems intuitive, it's not correct according to the specification. Node.js 10 implements the correct behavior, which is to first execute the chained handlers, and only afterwards continue with the async function."

**[fact]** Against the es2017 model, Node 8 fails 3,069 of 9,430. The smallest counterexample is the blog's example minus one handler:
```
(async()=>{await P;log("A0")})(); P.then(()=>log("P1"));
es2017 expects P1,A0   node8 got A0,P1
```
- **[fact]** Node 10 and 11 pass this class.
- **[fact, nuance]** Against es2019, Node 8 passes this class, because the "bug" became the spec. The checker is therefore only as good as the spec version you pin, which is why the model takes a parameter.

### Bug 3 (new, unreported): Boa `SimpleJobExecutor`

Source: https://github.com/boa-dev/boa/blob/329e89748ed34e218fe593b4209b1dbe1d6eb64d/core/engine/src/job.rs, `run_jobs_async`, original lines ~949–1048. Its doc comments say:
> "A simple FIFO executor that bails on the first error."

> "This is the default job executor for the [`Context`], but it is mostly pretty limited for a custom event loop."

**[fact]** Each loop iteration does three things in this order:
1. "Dispatch all past-due timeout jobs" runs every due timer back to back;
2. `let jobs = mem::take(&mut *self.promise_jobs.borrow_mut())` runs a snapshot of the promise queue;
3. it loops.

The clock is `std::time::Instant`-based, so a 0 ms timer is always already due at the next iteration. **[fact]** Three failure classes were observed, all at the 680 bound:
1. **Timer before the script's own microtasks.** 148 of 212 failures; e.g. `setTimeout(T0); P.then(P1)` gives `T0,P1`.
2. **Snapshot defect.** A microtask queued while draining waits behind timers. E.g. `P.then(()=>{log("P0"); setTimeout(T1); P.then(P2)})` should give `P0,P2,T1`; Boa gives `P0,T1,P2`.
3. **Timer batching**, the same as Node ≤10.

**[fact]** No program without `setTimeout` fails, so promise-job FIFO itself is correct in Boa.

Prior Boa issues I found are related but different. They are about timers being lost or starved, not about ordering:
- boa-dev/boa#4706 (https://github.com/boa-dev/boa/pull/4706): "Multiple `setTimeout(..., 0)` calls at the same instant caused silent overwrites"
- #4782 (https://github.com/boa-dev/boa/issues/4782): "Timeout jobs that are scheduled for the current instant ( now ) may never run."
- #5308 (https://github.com/boa-dev/boa/issues/5308): "These tests pass under `boa_tester`, which uses `SimpleJobExecutor`, but hang under the CLI executor"

The issue/PR search was done by a sub-agent. It says api.github.com was blocked, so it used `.patch` files and WebFetch. Treat "no prior report exists" as **[belief]**, not fact.

**[opinion]** Severity is moderate:
- every embedder who calls `boa_runtime::register` with the default `Context` gets non-HTML timer/promise ordering;
- the doc says the executor is "limited", but nothing says it violates microtask-checkpoint semantics.

### Bug 4 (new, unreported): Boa CLI executor, flaky

- **[fact]** `cli/src/executor.rs` runs promise jobs, generic jobs and async jobs (timers are wrapped as `NativeAsyncJob`s) as three separate smol tasks. Its comment says:
  > "Continually run all pending promise jobs, yielding to the async executor after every successful run."
- **[fact] Observed failures.** Timer batching (`T0,T2,P1`), and microtask overtaking. For example, `setTimeout(T0); (async()=>{await P; log("A1"); (async()=>{await P; log("A2")})()})()` should give `A1,A2,T0`; it gave `A1,T0,A2`.
- **[inference]** Mechanism (I did not trace it in a debugger): `run_promise_jobs` takes a `mem::take` snapshot and then `yield_now()`, so the timer task can run between snapshots. In addition, `run_async_jobs` can complete a second ready timer before the promise task is polled.

## 6. Fix (Boa `SimpleJobExecutor`)

- **[fact]** The patch (Appendix E) adds `drain_promise_jobs`, which pops until empty (HTML checkpoint semantics), and calls it:
  - before dispatching timers;
  - after each timeout and each interval callback;
  - in place of the old `mem::take` snapshot.
- Verification of the patch:
  - conformance: 0 of 9,430 failures;
  - TLA+ `boa_fixed`: no violation at Budget 8;
  - Verus `run_jobs_patched`: verified;
  - `cargo test -p boa_engine --lib job`: 2 passed;
  - `cargo test -p boa_wintertc`: 54 + 1 passed.
- Not run: the full Boa test suite and test262.
- **[opinion]** Generic jobs (`GenericJob`) are still run as a snapshot after promise jobs. That is outside this property, but worth a look before upstreaming.

## 7. Blockers and limits

- **What "bounded" means here.** Conformance means completeness up to the grammar and bound (≤4 callbacks, depth ≤4, delay 0 only). Not covered: nonzero delays and the nesting clamp, `setInterval`, events/DOM tasks, `MutationObserver`, unhandled rejections, thenable adoption, async generators, `process.nextTick`/`setImmediate`, and multiple task sources and their priorities.
- **Real binaries are a black box.** Timing-dependent bugs (Node ≤10, Boa CLI) show up statistically, not every run. A failing case is a real counterexample; a pass is not a proof.
- **The TLA+ and Verus models are hand abstractions of the Rust code.** Nothing mechanically links them to `job.rs`, so the abstraction gap is unverified. **[opinion]** That is the main obstacle to "verify the implementation" in Verus.
  - Verus cannot directly check Boa's real `run_jobs_async`: it uses `async`, `RefCell`, `Rc<dyn …>` closures and `futures_concurrency::FutureGroup`, which Verus does not support.
  - A realistic path is to refactor the scheduler into a pure, Verus-checked state machine that the async shell calls. My `Q` struct is a sketch of that.
- **The model is validated against Chromium, not against the spec text.** Its agreement with Chromium, Node 12 and Node 22 is evidence that the model is right, not proof. Chromium agreeing on 9,430 programs is itself only a bounded check of Chromium.
- **Toolchain friction.**
  - Python Playwright is not installed; Node's `playwright` is.
  - In Chromium, `page.setContent` reuses the JS realm, so `const` redeclaration broke runs; fixed by navigating to `data:` URLs.
  - The Boa CLI prints the script's completion value; fixed by filtering lines to the label regex.
  - Verus now requires `final(self)` in `ensures` for `&mut` parameters.

## 8. Reproduce

All of this is in an ephemeral container. Code bundle: `/home/user/p2/p2_event_loop_code.tgz` (not persisted); every file needed is inlined in the appendices.
```
# conformance
python3 conf/run.py 4 4 node10 node22 boa-simple boa-simple-fixed boa-cli chromium
# TLA+
java -cp tla2tools.jar tlc2.TLC -config boa_simple_5.cfg EventLoop.tla   # Impl ∈ html|node10|boa_simple|boa_fixed
# Verus (rolling 0.2026.11.04.d804d56, toolchain 1.99.1)
verus verus/event_loop.rs            # 10 verified, 0 errors
verus verus/event_loop_original.rs   # (= same file without the #[cfg]) 1 error at run_timer
```
TLA+ cfg: `CONSTANTS Impl = "boa_simple"  Budget = 5` / `SPECIFICATION Spec` / `INVARIANTS TypeOK NoTaskWithPendingMicrotasks MicroFIFO TaskFIFO` / `CHECK_DEADLOCK FALSE`.

---
## Appendix A: reference model + program generator (`conf/model.py`)
```python
"""Executable reference model of the HTML event loop + ECMAScript promise jobs,
restricted to a tiny program grammar, plus a bounded enumerator of programs.

Grammar (a program is a forest; every node = one callback with a unique label):
  T  setTimeout(cb, 0)                         -> HTML timer task
  M  queueMicrotask(cb)                        -> microtask
  P  P.then(cb)          (P = Promise.resolve(), created once, already fulfilled)
  C  P.then(cb).then(()=>log(label+"'"))       -> chained reaction
  A  (async()=>{ await P; cb })()              -> async fn resumption
Each callback logs its label, then executes its children in order.

Semantics encoded (spec text quoted in report):
  - HTML: after each task, perform a microtask checkpoint = run microtasks until
    the queue is empty (including ones enqueued during the checkpoint).
  - HTML timers: equal-delay timers run in creation order, one task each.
  - ECMA-262: promise jobs run FIFO in HostEnqueuePromiseJob order; queueMicrotask
    shares the same microtask queue.
  - `await P` (P a native fulfilled promise):
      es2019+: 1 job (PromiseResolve returns P; PerformPromiseThen enqueues now)
      es2017 : 3 jobs (NewPromiseResolveThenableJob -> P.then reaction -> resume)
"""
from collections import deque
import itertools

KINDS = "TMPCA"


def forests(n, depth):
    """All ordered forests with exactly n nodes, max depth `depth`, kinds in KINDS."""
    if n == 0:
        yield ()
        return
    if depth == 0:
        return
    # first tree has k nodes (1 root + k-1 descendants), rest of forest n-k
    for k in range(1, n + 1):
        for kind in KINDS:
            for kids in forests(k - 1, depth - 1):
                for rest in forests(n - k, depth):
                    yield ((kind, kids),) + rest


def label(prog):
    """Attach unique labels: returns forest of (kind, lbl, kids)."""
    ctr = itertools.count()

    def go(f):
        out = []
        for kind, kids in f:
            lbl = f"{kind}{next(ctr)}"
            out.append((kind, lbl, go(kids)))
        return tuple(out)

    return go(prog)


def to_js(lprog, polyfill_qm=False):
    def body(f, ind):
        s = []
        for kind, lbl, kids in f:
            inner = f'log("{lbl}");' + body(kids, ind + 1)
            cb = f"()=>{{{inner}}}"
            if kind == "T":
                s.append(f"setTimeout({cb},0);")
            elif kind == "M":
                s.append(f"queueMicrotask({cb});")
            elif kind == "P":
                s.append(f"P.then({cb});")
            elif kind == "C":
                s.append(f"P.then({cb}).then(()=>log(\"{lbl}'\"));")
            elif kind == "A":
                s.append(f"(async()=>{{await P;{inner}}})();")
        return "".join(s)

    pre = ""
    if polyfill_qm:
        pre = ('if(typeof queueMicrotask!=="function"){'
               '(typeof globalThis!=="undefined"?globalThis:global).queueMicrotask=f=>{Promise.resolve().then(f)};}')
    return (pre + 'const log=(x)=>console.log(x);const P=Promise.resolve();'
            + body(lprog, 0))


def run_model(lprog, await_ticks=1):
    """Return the log trace the spec mandates."""
    out = []
    tasks = deque()   # HTML task queue (timers only; all delay 0 -> FIFO)
    micro = deque()   # single microtask queue

    def exec_forest(f):
        for kind, lbl, kids in f:
            cb = (lambda l=lbl, k=kids: (out.append(l), exec_forest(k)))
            if kind == "T":
                tasks.append(cb)
            elif kind in "MP":
                micro.append(cb)
            elif kind == "C":
                def first(cb=cb, l=lbl):
                    cb()                       # reaction handler runs,
                    micro.append(lambda: out.append(l + "'"))  # then derived promise fulfils
                micro.append(first)
            elif kind == "A":
                # async fn body runs synchronously up to `await P`
                def chain(n, cb=cb):
                    if n == 1:
                        return cb
                    return lambda: micro.append(chain(n - 1, cb))
                micro.append(chain(await_ticks))

    def checkpoint():
        while micro:
            micro.popleft()()

    exec_forest(lprog)   # the script task
    checkpoint()
    while tasks:
        tasks.popleft()()
        checkpoint()      # microtask checkpoint after EACH task
    return out


if __name__ == "__main__":
    import sys, json
    n, d = int(sys.argv[1]), int(sys.argv[2])
    progs = [p for k in range(1, n + 1) for p in forests(k, d)]
    print(len(progs), file=sys.stderr)
```

## Appendix B: TLA+ (`tla/EventLoop.tla`)
```tla
---------------------------- MODULE EventLoop ----------------------------
(***************************************************************************)
(* Abstract event loop: one macrotask (timer) queue, one microtask queue.  *)
(* Every job, when run, may enqueue up to 2 new jobs (microtask "M" or     *)
(* 0-delay timer "T"), with a global budget of Budget jobs.                *)
(*                                                                         *)
(* Impl selects the scheduling algorithm:                                  *)
(*  "html"       HTML spec: run 1 task, then drain microtasks to empty.    *)
(*  "node10"     Node<=10 timers: run every already-expired timer back to  *)
(*               back, then drain microtasks (lib/timers.js listOnTimeout).*)
(*  "boa_simple" Boa SimpleJobExecutor::run_jobs_async (core/engine/src/   *)
(*               job.rs): per loop iteration, run all due timers back to   *)
(*               back, then run a *snapshot* of the promise queue          *)
(*               (mem::take); jobs enqueued meanwhile wait one iteration.  *)
(*                                                                         *)
(* Safety property (HTML "perform a microtask checkpoint" after each task):*)
(*   NoTaskWithPendingMicrotasks: a macrotask never starts while a         *)
(*   microtask is pending.                                                 *)
(* Also checked: MicroFIFO (microtasks start in enqueue order) and         *)
(* TaskFIFO (timers start in enqueue order).                               *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Impl, Budget

VARIABLES micro,   \* pending microtask ids (FIFO)
          tasks,   \* pending timer ids (FIFO; all delay 0)
          batch,   \* boa/node10: timers selected as "due" for this round
          snap,    \* boa: snapshot of promise jobs being run this round
          phase,   \* boa/node10: "timers" | "micro"
          nextId,  \* id counter == number of jobs created so far
          startedM,\* ids of microtasks in start order
          startedT,\* ids of timers in start order
          enqM,    \* ids of microtasks in enqueue order
          enqT,    \* ids of timers in enqueue order
          bad      \* TRUE once a task started while a microtask was pending

vars == <<micro, tasks, batch, snap, phase, nextId, startedM, startedT, enqM, enqT, bad>>

Kinds == {"M", "T"}
\* all spawn sequences of length <= 2 that fit the budget
Spawns(n) == {s \in UNION {[1..k -> Kinds] : k \in 0..2} : n + Len(s) <= Budget}

\* ids assigned to a spawn sequence s starting at nextId
MIds(s, n) == [i \in 1..Len(SelectSeq([j \in 1..Len(s) |-> <<j, s[j]>>], LAMBDA p: p[2] = "M")) |->
                 n + SelectSeq([j \in 1..Len(s) |-> <<j, s[j]>>], LAMBDA p: p[2] = "M")[i][1]]
TIds(s, n) == [i \in 1..Len(SelectSeq([j \in 1..Len(s) |-> <<j, s[j]>>], LAMBDA p: p[2] = "T")) |->
                 n + SelectSeq([j \in 1..Len(s) |-> <<j, s[j]>>], LAMBDA p: p[2] = "T")[i][1]]

\* effect of running a job that spawns s: append new ids to the queues
Spawn(s, m, t) ==
    /\ micro' = m \o MIds(s, nextId)
    /\ tasks' = t \o TIds(s, nextId)
    /\ enqM'  = enqM \o MIds(s, nextId)
    /\ enqT'  = enqT \o TIds(s, nextId)
    /\ nextId' = nextId + Len(s)

\* the script (itself a task) runs in Init and spawns anything
Init == \E s \in Spawns(0):
          /\ micro = MIds(s, 0) /\ tasks = TIds(s, 0)
          /\ enqM = micro /\ enqT = tasks
          /\ nextId = Len(s)
          /\ batch = <<>> /\ snap = <<>> /\ phase = "micro"
          /\ startedM = <<>> /\ startedT = <<>> /\ bad = FALSE

PendingMicro == micro /= <<>> \/ snap /= <<>>

RunMicro(fromSnap) ==   \* run head of micro (html/node10) or of snap (boa)
    \E s \in Spawns(nextId):
      IF fromSnap
      THEN /\ startedM' = Append(startedM, Head(snap))
           /\ snap' = Tail(snap)
           /\ Spawn(s, micro, tasks)
      ELSE /\ startedM' = Append(startedM, Head(micro))
           /\ snap' = snap
           /\ Spawn(s, Tail(micro), tasks)

RunTask(id, t) ==       \* start timer `id`; t = timer queue after removal
    \E s \in Spawns(nextId):
      /\ startedT' = Append(startedT, id)
      /\ bad' = (bad \/ PendingMicro)
      /\ Spawn(s, micro, t)

\* ---------------- HTML spec ----------------
HtmlNext ==
    \/ micro /= <<>> /\ RunMicro(FALSE)
       /\ UNCHANGED <<batch, phase, startedT, bad>>
    \/ micro = <<>> /\ tasks /= <<>> /\ RunTask(Head(tasks), Tail(tasks))
       /\ UNCHANGED <<batch, snap, phase, startedM>>

\* ---------------- Node <= 10 ----------------
\* phase "micro": drain microtasks fully; when empty, every pending timer is
\* already expired (delay 0) -> move them all into batch, phase "timers".
\* phase "timers": run batch back to back, no checkpoint in between.
Node10Next ==
    \/ phase = "micro" /\ micro /= <<>> /\ RunMicro(FALSE)
       /\ UNCHANGED <<batch, phase, startedT, bad>>
    \/ phase = "micro" /\ micro = <<>> /\ tasks /= <<>>
       /\ batch' = tasks /\ tasks' = <<>> /\ phase' = "timers"
       /\ UNCHANGED <<micro, snap, nextId, startedM, startedT, enqM, enqT, bad>>
    \/ phase = "timers" /\ batch /= <<>>
       /\ RunTask(Head(batch), tasks) /\ batch' = Tail(batch)
       /\ UNCHANGED <<snap, phase, startedM>>
    \/ phase = "timers" /\ batch = <<>> /\ phase' = "micro"
       /\ UNCHANGED <<micro, tasks, batch, snap, nextId, startedM, startedT, enqM, enqT, bad>>

\* ---------------- Boa SimpleJobExecutor ----------------
\* loop { run all due timers; snap := take(promise_jobs); run snap; }
\* (0-delay timers are due at the next iteration: modelled as "all pending")
BoaNext ==
    \/ phase = "micro" /\ snap = <<>> /\ (micro /= <<>> \/ tasks /= <<>>)
       \* new loop iteration: select due timers
       /\ batch' = tasks /\ tasks' = <<>> /\ phase' = "timers"
       /\ UNCHANGED <<micro, snap, nextId, startedM, startedT, enqM, enqT, bad>>
    \/ phase = "timers" /\ batch /= <<>>
       /\ RunTask(Head(batch), tasks) /\ batch' = Tail(batch)
       /\ UNCHANGED <<snap, phase, startedM>>
    \/ phase = "timers" /\ batch = <<>>
       \* let jobs = mem::take(&mut promise_jobs)
       /\ snap' = micro /\ micro' = <<>> /\ phase' = "micro"
       /\ UNCHANGED <<tasks, batch, nextId, startedM, startedT, enqM, enqT, bad>>
    \/ phase = "micro" /\ snap /= <<>> /\ RunMicro(TRUE)
       /\ UNCHANGED <<batch, phase, startedT, bad>>

\* ---------------- Boa SimpleJobExecutor, patched ----------------
\* loop { drain(micro); due := all timers; for t in due { run t; drain(micro) } }
\* phase "micro": drain fully; phase "timers": run one timer then go to
\* phase "tmicro" which drains fully before the next timer of the batch.
BoaFixedNext ==
    \/ phase \in {"micro", "tmicro"} /\ micro /= <<>> /\ RunMicro(FALSE)
       /\ UNCHANGED <<batch, phase, startedT, bad>>
    \/ phase = "micro" /\ micro = <<>> /\ tasks /= <<>>
       /\ batch' = tasks /\ tasks' = <<>> /\ phase' = "timers"
       /\ UNCHANGED <<micro, snap, nextId, startedM, startedT, enqM, enqT, bad>>
    \/ phase = "timers" /\ batch /= <<>>
       /\ RunTask(Head(batch), tasks) /\ batch' = Tail(batch) /\ phase' = "tmicro"
       /\ UNCHANGED <<snap, startedM>>
    \/ phase = "tmicro" /\ micro = <<>> /\ phase' = "timers"
       /\ UNCHANGED <<micro, tasks, batch, snap, nextId, startedM, startedT, enqM, enqT, bad>>
    \/ phase = "timers" /\ batch = <<>> /\ phase' = "micro"
       /\ UNCHANGED <<micro, tasks, batch, snap, nextId, startedM, startedT, enqM, enqT, bad>>

Done == micro = <<>> /\ tasks = <<>> /\ batch = <<>> /\ snap = <<>>

Next == \/ Impl = "html" /\ HtmlNext
        \/ Impl = "node10" /\ Node10Next
        \/ Impl = "boa_simple" /\ BoaNext
        \/ Impl = "boa_fixed" /\ BoaFixedNext
        \/ Done /\ UNCHANGED vars

Spec == Init /\ [][Next]_vars

\* ---------------- Properties ----------------
NoTaskWithPendingMicrotasks == ~bad
IsPrefix(a, b) == Len(a) <= Len(b) /\ SubSeq(b, 1, Len(a)) = a
MicroFIFO == IsPrefix(startedM, enqM)
TaskFIFO  == IsPrefix(startedT, enqT)
TypeOK == nextId <= Budget
=============================================================================
```

## Appendix C: Verus (`verus/event_loop.rs`)
```rust
// Verus model of Boa SimpleJobExecutor's scheduling core (core/engine/src/job.rs),
// abstracted: a job is an opaque id; running it may enqueue arbitrary new
// microtasks / 0-delay timers (`run_job` is an unverified oracle).
// Queues are Vec + head index (FIFO). Property checked at every timer start:
//   HTML "perform a microtask checkpoint" after each task  ==>
//   a timer task never starts while a microtask is pending.
// Plus FIFO: started microtasks == enqueued microtasks[0..head].
use vstd::prelude::*;

verus! {

pub struct Item { pub is_timer: bool, pub id: u64 }

// Oracle: the JS callback runs and returns what it enqueued. No spec => any output.
#[verifier::external_body]
fn run_job(id: u64) -> (out: Vec<Item>) { unimplemented!() }

pub struct Q { pub micro: Vec<u64>, pub hm: usize, pub timers: Vec<u64>, pub ht: usize,
               pub started_m: Ghost<Seq<u64>> }

impl Q {
    pub open spec fn inv(&self) -> bool {
        &&& self.hm <= self.micro@.len()
        &&& self.ht <= self.timers@.len()
        &&& self.started_m@ == self.micro@.subrange(0, self.hm as int)   // FIFO
    }
    pub open spec fn micro_empty(&self) -> bool { self.hm == self.micro@.len() }

    fn push_all(&mut self, items: Vec<Item>)
        requires old(self).inv()
        ensures final(self).inv(), final(self).hm == old(self).hm, final(self).ht == old(self).ht,
                final(self).timers@.len() >= old(self).timers@.len(),
                final(self).micro@.subrange(0, final(self).hm as int) == old(self).micro@.subrange(0, old(self).hm as int),
                final(self).started_m@ == old(self).started_m@,
                final(self).micro@.len() >= old(self).micro@.len(),
    {
        let mut i = 0;
        while i < items.len()
            invariant self.inv(), self.hm == old(self).hm, self.ht == old(self).ht,
                      self.timers@.len() >= old(self).timers@.len(),
                      self.started_m@ == old(self).started_m@,
                      self.micro@.len() >= old(self).micro@.len(),
                      self.micro@.subrange(0, self.hm as int) == old(self).micro@.subrange(0, old(self).hm as int),
            decreases items.len() - i,
        {
            if items[i].is_timer { self.timers.push(items[i].id); }
            else {
                let ghost before = self.micro@;
                self.micro.push(items[i].id);
                assert(self.micro@.subrange(0, self.hm as int) =~= before.subrange(0, self.hm as int));
            }
            i += 1;
        }
    }

    fn run_micro(&mut self)
        requires old(self).inv(), !old(self).micro_empty()
        ensures final(self).inv(), final(self).hm == old(self).hm + 1, final(self).ht == old(self).ht,
                final(self).timers@.len() >= old(self).timers@.len(),
                final(self).micro@.len() >= old(self).micro@.len(),
    {
        let _len = self.micro.len();   // usize bound => hm + 1 cannot overflow
        let id = self.micro[self.hm];
        self.started_m = Ghost(self.started_m@.push(id));
        self.hm += 1;
        assert(self.started_m@ =~= self.micro@.subrange(0, self.hm as int));
        let out = run_job(id);
        self.push_all(out);
    }

    // HTML "perform a microtask checkpoint": drain until empty (incl. new ones)
    #[verifier::exec_allows_no_decreases_clause]
    fn drain(&mut self)
        requires old(self).inv()
        ensures final(self).inv(), final(self).micro_empty(), final(self).ht == old(self).ht,
                final(self).timers@.len() >= old(self).timers@.len(),
    {
        while self.hm < self.micro.len()
            invariant self.inv(), self.ht == old(self).ht,
                      self.timers@.len() >= old(self).timers@.len(),
        { self.run_micro(); }
    }

    fn run_timer(&mut self)
        requires old(self).inv(), old(self).ht < old(self).timers@.len(),
                 old(self).micro_empty()          // <-- THE PROPERTY, checked at every call site
        ensures final(self).inv(), final(self).ht == old(self).ht + 1, final(self).hm == old(self).hm,
                final(self).timers@.len() >= old(self).timers@.len(),
    {
        let _len = self.timers.len();
        let id = self.timers[self.ht];
        self.ht += 1;
        let out = run_job(id);
        self.push_all(out);
    }
}

// Patched SimpleJobExecutor::run_jobs_async (this report's fix).
#[verifier::exec_allows_no_decreases_clause]
fn run_jobs_patched(q: &mut Q)
    requires old(q).inv()
    ensures final(q).micro_empty(), final(q).ht == final(q).timers@.len()
{
    loop
        invariant q.inv()
        ensures q.inv(), q.micro_empty(), q.ht == q.timers@.len()
    {
        q.drain();                               // checkpoint before timers
        let due = q.timers.len();                // all 0-delay timers are due
        while q.ht < due
            invariant q.inv(), q.micro_empty(), due <= q.timers@.len()
        {
            q.run_timer();
            q.drain();                           // checkpoint after EACH timer
        }
        if q.ht == q.timers.len() { break; }
    }
}

// Original SimpleJobExecutor::run_jobs_async structure. Expected: Verus REJECTS
// the `run_timer` precondition (micro_empty) -- the bug.
#[cfg(feature = "original")]
#[verifier::exec_allows_no_decreases_clause]
fn run_jobs_original(q: &mut Q)
    requires old(q).inv()
{
    loop
        invariant q.inv()
    {
        let due = q.timers.len();
        while q.ht < due                          // all due timers, back to back
            invariant q.inv(), due <= q.timers@.len()
        { q.run_timer(); }
        let snap_end = q.micro.len();            // mem::take(promise_jobs) snapshot
        while q.hm < snap_end
            invariant q.inv(), snap_end <= q.micro@.len()
        { q.run_micro(); }
        if q.hm == q.micro.len() && q.ht == q.timers.len() { break; }
    }
}

fn main() {}
} // verus!
```

## Appendix D: Boa harness (`examples/src/bin/p2_simple_exec.rs`)
```rust
//! p2 harness: run each line of a file as a separate JS program in a fresh
//! `Context::default()` (=> `SimpleJobExecutor`, the engine's default event loop),
//! with the boa_runtime extensions (console, setTimeout, queueMicrotask).
//! Prints "@@<idx>" before each program's output.
use boa_engine::{Context, Source};
use boa_runtime::extensions::ConsoleExtension;
use std::io::Write;

fn main() {
    let path = std::env::args().nth(1).expect("usage: p2_simple_exec <file>");
    let text = std::fs::read_to_string(path).unwrap();
    for (i, line) in text.lines().enumerate() {
        println!("@@{i}");
        let mut ctx = Context::default();
        boa_runtime::register(ConsoleExtension::default(), None, &mut ctx).unwrap();
        if let Err(e) = ctx.eval(Source::from_bytes(line)) {
            println!("!!eval error {e}");
        }
        if let Err(e) = ctx.run_jobs() {
            println!("!!job error {e}");
        }
        std::io::stdout().flush().unwrap();
    }
}
```

## Appendix E: Boa patch (against 329e8974 `core/engine/src/job.rs`)
```diff
--- /home/user/p2/job.rs.orig	2026-11-04 06:53:02.446547485 +0000
+++ core/engine/src/job.rs	2026-11-04 06:56:43.091004841 +0000
@@ -906,6 +906,16 @@
         Arc::clone(&self.stop)
     }
 
+    /// HTML "perform a microtask checkpoint": run promise jobs until the queue
+    /// is empty, including jobs enqueued while draining.
+    fn drain_promise_jobs(&self, context: &RefCell<&mut Context>) -> JsResult<()> {
+        loop {
+            let job = self.promise_jobs.borrow_mut().pop_front();
+            let Some(job) = job else { return Ok(()) };
+            job.call(&mut context.borrow_mut())?;
+        }
+    }
+
     pub(crate) fn is_empty(&self) -> bool {
         self.promise_jobs.borrow().is_empty()
             && self.async_jobs.borrow().is_empty()
@@ -967,6 +977,11 @@
                 fr_group.insert(job.call(context));
             }
 
+            if let Err(err) = self.drain_promise_jobs(context) {
+                self.clear();
+                return Err(err);
+            }
+
             // Dispatch all past-due timeout jobs before the termination check.
             {
                 let now = context.borrow().clock().now();
@@ -989,19 +1004,29 @@
                                         self.clear();
                                         return Err(err);
                                     }
+                                    if let Err(err) = self.drain_promise_jobs(context) {
+                                        self.clear();
+                                        return Err(err);
+                                    }
                                 }
                                 ClockJob::Interval(job) => {
-                                    let context = &mut context.borrow_mut();
-                                    let now = context.clock().now();
-                                    if let Err(err) = job.call(context) {
+                                    {
+                                        let context = &mut context.borrow_mut();
+                                        let now = context.clock().now();
+                                        if let Err(err) = job.call(context) {
+                                            self.clear();
+                                            return Err(err);
+                                        }
+                                        self.clock_jobs
+                                            .borrow_mut()
+                                            .entry(now + job.interval())
+                                            .or_default()
+                                            .push(ClockJob::Interval(job));
+                                    }
+                                    if let Err(err) = self.drain_promise_jobs(context) {
                                         self.clear();
                                         return Err(err);
                                     }
-                                    self.clock_jobs
-                                        .borrow_mut()
-                                        .entry(now + job.interval())
-                                        .or_default()
-                                        .push(ClockJob::Interval(job));
                                 }
                             }
                         }
@@ -1025,12 +1050,9 @@
                 return Err(err);
             }
 
-            let jobs = mem::take(&mut *self.promise_jobs.borrow_mut());
-            for job in jobs {
-                if let Err(err) = job.call(&mut context.borrow_mut()) {
-                    self.clear();
-                    return Err(err);
-                }
+            if let Err(err) = self.drain_promise_jobs(context) {
+                self.clear();
+                return Err(err);
             }
 
             let jobs = mem::take(&mut *self.generic_jobs.borrow_mut());
```

# Current Tokio `Notify`: cancellation permit check
(authored by agents unless marked 🧑)

result, 2026-11-18 UTC, Tokio master `fc0d151` (tokio 1.54.1)
- property: dropping a `Notified` future never loses a pending `notify_one` permit
  - checked as a stronger statement: no step except a receive (a future consuming the permit and completing) turns "a permit is pending" from true to false
  - permit pending: `state == NOTIFIED`, or a `Waiting` future holds notification `One`, or the lock holder is a future that removed its own `One` and has not re-delivered it
- holds under the trust listed below; no counterexample
  - `tokio_current.py` on the real MIR: `abstract shared states: 9693; lock-free thread configurations: 247`, `permit-losing non-receive steps: 0 (by drop: 0)`, `reachable panics: []`, exit 0
  - covers every number of futures and threads, every interleaving at the stated granularity, and C11-stale loads of `state`; it is an exhaustive search of a finite sound abstraction, not a Verus proof
- mutations of the real MIR (each a one-line change in one function), all rejected
  - `drop_unguarded_store` (drop stores EMPTY whenever the list is empty, the pre-#3652 shape): counterexample, 36 permit-losing drop steps
  - `drop_no_forward` (drop ignores a received `One`): counterexample, 36
  - `locked_err_no_store` (`notify_locked` skips the store after a failed CAS): counterexample, 9
  - `locked_unconditional_empty` (WAITING arm stores EMPTY even with waiters left): exit 2, rejected by the checked assumption that a counter change moves the whole waiter list
- loom, `LOOM_MAX_PREEMPTIONS=2`, [patch](real_tokio/current-loom.patch) adding 3 tests
  - master: all 12 `loom_notify` tests pass (`test result: ok. 12 passed`)
  - master with the #3652 guard removed from `drop_notified` (`if waiters.is_empty() {`): our `drop_vs_notify_waiters_and_one` fails with `permit lost`; Tokio's 9 existing loom Notify tests and our other 2 pass

method
- [tokio_current.py](tokio_current.py) executes the real compiled MIR, statement by statement, of
  - `notify_with_strategy` (`notify_one`, `notify_last`), `notify_locked`
  - `Notify::notify_waiters` → `lock_waiter_list` → `NotifyGuard::notify_waiters` → `inner_notify_waiters`
  - `NotifiedProject::poll_notified`, `NotifiedProject::drop_notified`
  - no operation of these functions is modelled by hand; branches, loops, drop flags, `assert!`/`unwrap` panics and calls between them come from MIR
- abstract state
  - `state` word: the 2 state bits; the notify_waiters counter is not stored
  - Waiting futures counted by membership, saturating at 2: `main` list, a notify_waiters guarded list, unlinked with `One`, unlinked with `All`; Init and Done futures are unbounded and untracked
  - the mutex holder is tracked exactly (call stack and locals); threads not holding it form a growing set, and any configuration once reachable may be occupied by any number of threads afterwards
- one step runs from one interleaving point to the next: each access to `state`, each lock acquire, each lock-free read of a waiter's notification, and each loop back edge
- extraction: `--emit=mir` of `-p tokio --lib --features sync`, rustc 1.100.0, `RUSTC_BOOTSTRAP=1` ([build script](real_tokio/build_current.sh))

memory-ordering and atomicity assumptions
- checked in the abstraction (over-approximated, not assumed away)
  - a load of `state` while holding the lock returns WAITING exactly, but EMPTY and NOTIFIED interchangeably (may be stale)
  - a load without the lock returns any of the three
  - a lock-free read of a waiter's notification may return `None` when it is set
  - CAS by a non-holder whose expected value is stale may fail even when the state bits match
  - stores of `state` must use a value read under the currently held lock (else exit 2)
  - every counter change must be followed, within the same lock hold, by moving the whole `main` list to a guarded list (else exit 2)
- assumed (argued, not checked)
  - C11 facts: RMWs read the latest value in modification order; the mutex gives happens-before between critical sections; coherence then justifies the stale-load rules above
  - transitions into or out of WAITING occur only under the lock; this is what the code does, and the interpreter enforces it for list and notification operations
  - the counter never wraps (2^62 `notify_waiters` calls)
  - a Waiting future under the lock with no notification sees a changed counter exactly when it is in a guarded list
  - the lock-free notification read and the later `clear()` touch only the owner's waiter, which no other thread writes once its notification is set

trusted
- rustc MIR is faithful; `--features sync` build without loom equals the shipped code
- the interpreter (≈700 lines of Python, regex MIR parser) and its library semantics
  - `LinkedList::{push_front, pop_back, pop_front, remove, is_empty}`, `mem::take`, `NotifyWaitersList::{new, pop_back_locked}` (pop may also return `None` early, an over-approximation)
  - `AtomicNotification::{load, store_release, clear}` treated as primitives; their bit encodings were read, not checked
  - `Waker::wake`, waker clones, `WakeList` and `UnsafeCell::with_mut` have no effect on `Notify` state; user code in wakers is covered only as other threads calling `Notify`
- wrappers `Notified::{poll, drop}`, `OwnedNotified::{poll, drop}` and `project` call the checked functions; read in MIR, not checked
- out of scope: unwind paths, liveness (a waiter is eventually woken), memory safety of the intrusive list, `tokio_unstable` taskdump code (not compiled here)

prior work and what is new
- Tokio's loom tests at `fc0d151` exercise the real `Notify` for fixed small programs, bounded by preemptions
  - `notify_drop` drops a polled `Notified` concurrently with `notify_one`; it calls no `notify_waiters`
  - `notify_waiters_and_one` mixes the two calls but drops no pending future
  - observed: with the #3652 guard removed from current master, all 9 existing loom Notify tests pass; they do not cover that bug on current code
- new
  - a check over all numbers of futures and threads, derived from the compiled MIR of all five operations, under explicitly stated C11 rules; prior study ([TOKIO.md](TOKIO.md)) extracted only drop and `notify_locked`, at 2021 commits
  - three loom tests on current master; one detects the re-injected #3652 bug, which the existing loom suite misses
- must not claim
  - "Tokio's `Notify` is formally verified": the result is an abstract-interpretation search with a trusted Python interpreter, not a machine-checked refinement proof; it covers one safety property, normal paths only
  - loom covers more of the memory model for its small programs; ours covers more programs under a coarser memory model

run
- `bash real_tokio/build_current.sh SCRATCH END` (delete SCRATCH afterwards)
- from the repository root (each run ≈6 min on one core under `cpu-run LOW`)
  - `python3 -m verification.async_cancel.tokio_current SCRATCH/tokio-master.mir` exits 0
  - `... --mutate NAME` for each mutation above exits non-zero
  - `python3 -m verification.async_cancel.tokio_current_test SCRATCH/tokio-master.mir` runs all five; the numbers above came from the individual commands, run in parallel

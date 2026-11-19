# Current Tokio batch semaphore: cancellation and permit conservation
(authored by agents unless marked 🧑)

Result, 2026-11-19 UTC, Tokio master `fc0d151` (tokio 1.54.1), `tokio/src/sync/batch_semaphore.rs`: dropping an `Acquire` future never lost a permit in any explored execution. Separately, we found a permit leak on master when the semaphore is closed during a re-poll; a loom test reproduces it, and a second loom test shows its effect: a closed, drained bounded `mpsc` whose `recv()` never returns `None`. No prior report of it was found. Nothing was filed upstream.

Why this component
- the batch semaphore underlies Tokio's `Semaphore`, `Mutex`, `RwLock` and bounded `mpsc` (`Sender::reserve`/`send`)
- documented claim, `tokio/src/sync/semaphore.rs:586`: "Cancelling a call to `acquire` makes you lose your place in the queue." This implies that cancelling returns any permits already assigned
- recent cancellation bugs and fixes, all in Tokio 1.53/1.54
  - #8542 (`832dd233`, Alice Ryhl): "if the tracing subscriber panics during one of these events, the `Acquire` future is dropped without returning the permits to the semaphore"
  - #8541: "Tracing subscriber panic leaves a completed semaphore waiter linked (use-after-free)"
  - #8371 (`d241e4b5`) moved the coop-budget check after `poll_acquire`. Since then `Acquire::poll` can take permits and still return `Pending`; it relies on #8542's bookkeeping so that a later drop returns them

Property
- P1 conservation: whenever no operation is mid-flight, available permits + Σ over live, queued futures of (`num_permits − state`) + permits held by callers = initial + released − forgotten
- P2: at every terminal state, the wait queue is empty (no dangling waiter)
- P3: no reachable panic; P4: from every reachable state some terminal state is reachable
- cancellation is any drop of an `Acquire` between polls, including after a coop `Pending` that follows a successful acquisition

Results on master
- scenarios that never call `close`: all four properties hold
  - `three_futures` (1 initial permit; futures need 1, 1, 2; `release(2)`): 161191 states
  - `batch_partial` (1; 2, 2; `release(1)`, `release(2)`): 11201 states
  - `try_forget_open` (2; 2, 1; `try_acquire(1)`, `forget_permits(1)`, `release(1)`): 255276 states
  - each reports `P1 violations 0; P2 0; panics 0; stuck 0`
- scenarios that call `close`: P1 fails (`two_waiters_release_close`, `try_forget`)
  - this holds both with the stale-load over-approximation and with `--sc` (sequentially consistent loads only); see the trace below
  - P2, P3 and P4 hold there
- MIR mutations, on the scenarios that never close: all rejected
  - `pre8542_fast_path`: P1 violated (`batch_partial` 371 violating states, `three_futures` 3739); `try_forget_open` ran out of the 16G memory limit
  - `drop_no_return`: P1 violated in all three scenarios
  - `drop_no_remove`: P1 and P2 violated in all three (e.g. `three_futures`: P2 45)
  - `poll_clear_on_pending`: exit 2 in all three, `push_front` of a waiter that is already linked (the intrusive list would be corrupted)
  - `pre8542_fast_path`: the fast path neither records the permits in `state` nor sets `queued`. This is #8542's parent combined with master's #8371 order. Coop `Pending` followed by drop then leaks
  - `drop_no_return`: drop does not return assigned permits
  - `drop_no_remove`: drop does not unlink the waiter
  - `poll_clear_on_pending`: `queued` is cleared even on `Pending`

Counterexample: leak when `close` races a re-poll
- checker trace (`--sc`), one future needing 1 permit, semaphore starts at 0
  1. the future polls and is queued with `state = 1`
  2. it is polled again (a spurious or early poll; any poll is allowed). Since `queued` is set, `poll_acquire` loads `needed = state = 1`
  3. `release(2)` assigns 1 permit to the waiter (state 0, unlinked) and adds 1 to the counter
  4. the re-poll loads counter = 1 ≥ needed, so it takes the lock-free path: the CAS takes 1 permit (`remaining == 0`), and only then does it lock (`else if lock.is_none() { break self.waiters.lock(); }`)
  5. `close()` runs between that CAS and the lock
  6. the re-poll sees `waiters.closed` and returns `Err(AcquireError::closed())`. Its local `acquired` (1 permit) is dropped without being assigned or returned
  7. dropping the future returns only `num_permits − state` = 1; 1 permit is gone
- source, `batch_semaphore.rs` (`poll_acquire`): `if waiters.closed { return Poll::Ready(Err(AcquireError::closed())); }` runs after the CAS has subtracted permits held only in the local `acquired`
- running test: [real_tokio/semaphore-loom.patch.rs](real_tokio/semaphore-loom.patch.rs), appended to Tokio's `loom_semaphore_batch.rs` (`LOOM_MAX_PREEMPTIONS=3`)
  - on master: `repoll_assign_close_conserves_permits ... FAILED`, `assertion `left == right` failed: permit leaked`; Tokio's other 8 loom semaphore tests pass
- consequence on bounded `mpsc`: reproduced, 2026-11-19, loom test [real_tokio/mpsc-loom.patch.rs](real_tokio/mpsc-loom.patch.rs) appended to Tokio's `loom_mpsc.rs` (`LOOM_MAX_PREEMPTIONS=3`)
  - mechanism: `chan.rs:347` returns `None` only when `rx_fields.rx_closed && self.inner.semaphore.is_idle()` (available == bound); a leaked permit keeps `is_idle` false forever
  - scenario: `channel(2)` filled by `try_send`; a second `Sender` polls `reserve()` twice in one task; the receiver `try_recv`s both values, then `close()`s; a `Sender` stays alive; then `recv()` is polled once
  - master `fc0d151`: `close_after_repoll_recv_returns_none ... FAILED`, `recv() did not return None after close: slot permit leaked (capacity 1 of 2)`
  - control: master plus [real_tokio/semaphore-close-fix.patch](real_tokio/semaphore-close-fix.patch) (on the `waiters.closed` early return, add the locally `acquired` permits back to the counter): this test and `repoll_assign_close_conserves_permits` pass; all other `loom_semaphore_batch` tests and 17 other `loom_mpsc` tests pass. `loom_mpsc::try_recv` did not finish before the 4096 s `cpu-run` limit, so that run has no summary line. The patch is a candidate fix only; it was not reviewed beyond these tests
  - so `rx.close(); while let Some(_) = rx.recv().await {}`, the pattern in `Receiver::close`'s documentation, never ends while a `Sender` lives, given this interleaving. The trigger needs a second poll of a queued `reserve` future before it is woken; whether real executors or combinators (`select!`, `join!`, spurious wakeups) do this often is not measured
- not a cancellation (drop) bug: the drop path returns everything it owns. The leak is on the `close` path

Method
- [tokio_semaphore.py](tokio_semaphore.py) executes the real compiled MIR of `Acquire::poll`, `Acquire::project`, `Semaphore::poll_acquire`, `Waiter::assign_permits`, `Semaphore::add_permits_locked`, `<Acquire as Drop>::drop`, `release`, `close`, `try_acquire` and `forget_permits`, statement by statement, on concrete values
- a scenario fixes the initial permits and the actors, each on its own thread
  - a future may be polled any number of times, or dropped, in any order. After `Ready(Ok)` it is dropped, and its permits are either released or kept
  - `release`, `close`, `try_acquire` (then optionally release) and `forget_permits` each run once, or never
- exhaustive search over all interleavings at atomic accesses and lock acquisitions. Code between two such points runs atomically
- nondeterminism added on purpose (over-approximation)
  - `poll_proceed` (the coop budget) may return `Pending` at any poll
  - `compare_exchange_weak` may fail spuriously
  - a lock-free load of a waiter's `state` may return any value between the current one and the value at the owner's last store or lock acquisition
- extraction: `--emit=mir` of `-p tokio --lib --features sync`, rustc 1.100.0, `RUSTC_BOOTSTRAP=1` ([real_tokio/semaphore.sh](real_tokio/semaphore.sh))

Trusted, and limits
- bounded: up to 3 futures, up to 4 permits, the scenarios listed. This is a bounded model check of the real MIR, not a proof for all sizes. It is not a Verus proof and not a refinement proof
- rustc MIR is faithful; the `sync`-only build equals the shipped code (with the `rt` feature `poll_proceed` is real code; we treat it as arbitrary)
- the interpreter (Python, regex MIR parser) and its library semantics
  - the intrusive `LinkedList` as a sequence (`push_front`, `remove`, `last`, `pop_back`); `Mutex`; `Option`/`Result`/`Poll` helpers
  - wakers and `WakeList` have no effect on permits; `WakeList::can_push` is always true (capacity 32 exceeds the waiter count)
  - `trace_leaf` returns `Ready` (the taskdump feature is not compiled)
  - `Acquire::new` sets `state = num_permits`, `queued = false` (read in source, not interpreted)
- memory model: `permits` counter loads are sequentially consistent. Argued: every use of the loaded value either feeds a CAS (a stale value only makes it fail and reload) or tests the monotone CLOSED bit
- out of scope: unwind paths (the #8542 tracing-panic path is not compiled here), liveness (a waiter is eventually woken), memory safety of the intrusive list, `tokio_unstable` tracing code

Prior work, and what is new
- Tokio's loom suite `tokio/src/sync/tests/loom_semaphore_batch.rs` at master: 8 tests over the real code, bounded by preemptions, each a fixed small program
  - `concurrent_cancel` polls `acquire(1)` once, then drops it, against `release(10)`; `concurrent_close` mixes acquire, release and close; neither re-polls a queued waiter while it is assigned and the semaphore is closed
  - loom runs with no Tokio coop budget, so it never takes the coop-`Pending`-after-acquire path (inference from `poll_proceed`'s `.unwrap_or(Poll::Ready(...))` fallback when no runtime context exists)
- Tokio integration tests: `cancel_acquire_releases_permits` (`tests/sync_semaphore.rs`); `mutex_coop_drop_after_take_permit` (`tests/sync_mutex.rs`, added with #8371), which covers coop `Pending` then drop on one thread; the #8542 tracing-panic test in `tests/tracing_sync.rs`
- fuzzing: `tokio/fuzz` has only `fuzz_linked_list`
- papers
  - Koval, Khalanskiy, Alistarh, "CQS: A Formally-Verified Framework for Fair and Abortable Synchronization" ([arXiv:2111.12682](https://arxiv.org/abs/2111.12682)): a formally verified fair semaphore with cancellation, for Kotlin coroutines; a different algorithm and language, not Tokio's code
  - Li, Beschastnikh, Summers ([arXiv:2610.09198](https://arxiv.org/abs/2610.09198)), Section 7, list Tokio's Semaphore as a gap: "a wake-one primitive ... for single-permit synchronization idioms (e.g., tokio's Mutex, Semaphore)"
  - Lion (SOSP '26) verifies its own runtime, not Tokio's semaphore; see [LION.md](LION.md)
  - a web search for formal verification or model checking of Tokio's semaphore found nothing else; not exhaustive
- upstream: `gh search issues --repo tokio-rs/tokio semaphore leak` lists #8541, #2479, #2237 and others; none describes the close-path leak
- new
  - a check of permit conservation under cancellation for all action sequences and interleavings within the bounds, derived from the real master MIR, including coop `Pending` after acquisition and spurious re-polls
  - a permit leak in current master when `close` races a re-poll, found by the checker and reproduced by a loom test
  - the #8542 bookkeeping is shown to be necessary on master: removing it (`pre8542_fast_path`) is a cancellation leak through the coop path, not only through tracing panics
- must not claim
  - "Tokio's semaphore is verified". The positive result is bounded, covers normal paths only, excludes `close` (which fails), and trusts the interpreter
  - an `mpsc` hang observed in production; it is shown only in loom, for one interleaving

Run (from the repository root; delete SCRATCH afterwards)
- `bash verification/async_cancel/real_tokio/semaphore.sh SCRATCH END`: emits `SCRATCH/tokio.mir`, runs the loom tests; expected `loom exit: 101` with only `repoll_assign_close_conserves_permits` failing, then `mpsc loom exit: 101` (the `mpsc` test fails)
- `python3 -m verification.async_cancel.tokio_semaphore SCRATCH/tokio.mir [--sc] [--scenario NAME] [--mutate NAME]`: exit 0 = holds, 1 = violated, 2 = unsupported. With all scenarios, master exits 1 because of the close scenarios
- `python3 -m verification.async_cancel.tokio_semaphore_test SCRATCH/tokio.mir`: never-closed scenarios, unmutated and each mutation, one process per run (the numbers above came from individual runs in parallel; a single process holding all runs was killed at 16G)
- end-to-end run, 2026-11-19, rustc 1.100.0: `semaphore.sh` gave `loom exit: 101` (8 passed, 1 failed, as expected); `tokio_semaphore_test` exit 0: `unmutated three_futures: exit 0`, `batch_partial` 0, `try_forget_open` 0; `pre8542_fast_path: exits [1, 1, -9] (rejected)` (-9 = killed at the 16G limit, as in the individual runs); `drop_no_return` `[1, 1, 1]`; `drop_no_remove` `[1, 1, 1]`; `poll_clear_on_pending` `[2, 2, 2]`. No harness change was needed
- each scenario takes from about 10 s to several minutes on one core; run under `cpu-run LOW`

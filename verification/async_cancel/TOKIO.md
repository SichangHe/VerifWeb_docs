# Tokio `Notify` cancellation permit check
(authored by agents unless marked 🧑)

result, 2026-11-18 UTC
- bug: dropping (cancelling) a `Notified` future could erase a pending `notify_one` permit
  - upstream fix [tokio-rs/tokio#3652](https://github.com/tokio-rs/tokio/pull/3652), commit [`f7c181c`](https://github.com/tokio-rs/tokio/commit/f7c181c2c49ee28d7cb0773f5cdb4bec35b5a89b) (Tokio 1.4.0 era); parent `fee76ea7`
  - PR author's trace, quoted from the PR description:
    “`a.poll()` // adds a to waiters list, sets state to WAITING; `n.notify_waiters()` // removes a from waiters list, sets state to EMPTY; `n.notify_one()` // sets state to NOTIFIED; `drop(a)` // sets state to EMPTY; `n.notified().await` // waits forever”
- conditional safety proof for the real compiled Tokio code, buggy vs fixed
  - fixed `f7c181c`: all 6 MIR facts hold; Verus proves the obligation (`9 verified, 0 errors`)
  - parent `fee76ea7`: fact `drop_store_guarded` fails; Verus rejects (`8 verified, 1 errors`)
- Tokio's own regression `notify_one_after_dropped_all`
  - fixed: `test result: ok. 1 passed`
  - parent + test only ([patch](real_tokio/base-regression.patch)): panics at `tokio/tests/sync_notify.rs:152:5` (`assert_ready!`), `test result: FAILED`, exit 101
- `tokio_mir_test.py`: 5 checker-input mutations of the fixed MIR, one per fact; each is rejected

obligation proved
- in every reachable state of the modelled `Notify`, dropping a `Notified` future never loses a pending `notify_one` permit
  - permit pending: `Notify.state == NOTIFIED`, or some still-waiting future was assigned `Some(OneWaiter)`
  - formally: for every finite trace from the empty state and every drop step `s → t`, `permit(s) ⇒ permit(t)`
- holds for arbitrary interleavings of `notify_one`, `notify_waiters`, first poll, wake-up poll, and drops of listed, `OneWaiter`, `AllWaiters` and idle futures
- auxiliary invariant, also proved: `state == WAITING` exactly when the wait list is non-empty

connection to the real code
- [real_tokio/build.sh](real_tokio/build.sh) runs the regression on both commits and emits whole-crate MIR with rustc 1.100.0 (`-p tokio --features sync`, `RUSTC_BOOTSTRAP=1 --emit=mir`)
  - same fresh lockfile for both sides
  - `RUSTFLAGS=--cap-lints=warn`: Tokio 1.4 trips a lint that rustc 1.100 denies; lint levels do not change compiled code
- [tokio_mir.py](tokio_mir.py) replays every normal-return path of the two real functions, tracking each local's latest assignment
  - D1 `<Notified as Drop>::drop`: the lock, load and store happen only in the arm where `discriminant(*state) == 1` (`State::Waiting`)
  - D2 every `store` to `notify.state` lies on a path that took the non-zero arm of `LinkedList::is_empty` and arm `1` (WAITING) of `get_state(v)`, where `v` is still the value of `notify.state.load(SeqCst)`
    - the parent stores after `is_empty` alone; this is the bug
  - D3 the stored value is `set_state(_, EMPTY)`
  - D4 on the arm where the waiter's `notified` is `Some(OneWaiter)`, every path calls `notify_locked(waiters, &notify.state, v)` with `v` the current `notify_state` local
  - N1 `notify_locked`, arms EMPTY/NOTIFIED of `get_state(curr)`: every return path did `compare_exchange(curr, set_state(curr, NOTIFIED))`, and on its `Err` arm then stored `set_state(actual, NOTIFIED)`
  - N2 `notify_locked`, arm WAITING: every return path pops a waiter, writes `Some(OneWaiter)` into its `notified` field, and stores only `set_state(curr, EMPTY)` and only after `is_empty` returned true
- [tokio_obligations.py](tokio_obligations.py) writes the facts as booleans into a Verus transition system and runs Verus
  - a false fact weakens the matching transition (parent: drop stores EMPTY whenever the list is empty); Verus then fails at `drop_keeps_permit`
  - Verus proves the invariant inductively and lifts the drop obligation to every finite trace

trusted
- rustc MIR is faithful; discriminants follow declaration order (`State::Waiting` = 1, `NotificationType::OneWaiter` = 1, `Result::Err` = 1)
- the path replay in `tokio_mir.py` (regex parser, local tracking, function selection by header text)
- the other `Notify` operations are modelled from a source reading at the fixed commit, not extracted from MIR: `notify_one`, `notify_waiters`, `Notified::poll`
- atomicity: each step is one atomic transition
  - reasoned, not checked: transitions out of WAITING happen only under the waiters lock, and lock-free updates touch only EMPTY/NOTIFIED, so the fixed drop's guarded store cannot race
  - drop's `notify_locked` call uses a possibly stale EMPTY/NOTIFIED value; N1's `Err` arm stores NOTIFIED, so the model's “result is NOTIFIED” holds
- the 2-bit state and its `notify_waiters` call counter are abstracted to the state alone; the counter's early `Ready` in `poll` is omitted (it changes no permit)
- `LinkedList::remove/pop_back/is_empty` have their usual meaning; unwind and panic paths are out of scope

open gaps
- not the current Tokio: the result is for the 2021 code at these two commits; today's `Notify` was rewritten (per-waiter atomic `notification`), and is not checked
- liveness (the next `notified().await` actually completes) is covered only by the regression test
- `notify_one`, `notify_waiters` and `poll` are hand-modelled; a refinement proof would extract them too
- MIR-to-Verus abstraction and parser are unverified; this is a compiler-derived check, not a refinement proof
- unwind paths: `notify_locked` has `unwrap`/`assert!` panics; not analysed (see [UNWIND.md](UNWIND.md) for the method)

candidates checked first
- tokio#8542 (semaphore permit leak and use-after-free on tracing-subscriber panic): real, but reachable only with `tokio_unstable` + `tracing`, and (our judgment) proving it needs an intrusive-list memory-safety argument beyond these scripts; deferred
- Tokio's `cancel safety` search hits are documentation PRs, not fixes

run
- `bash real_tokio/build.sh SCRATCH END` (uses `cpu-run`; delete SCRATCH afterwards)
- from the repository root, with `VERUS_Z3_PATH` set to Z3 4.16.0
  - `uv run --no-project python -m verification.async_cancel.tokio_obligations SCRATCH/tokio-fixed.mir VERUS` exits 0
  - same with `tokio-parent.mir` exits 1
  - `uv run --no-project python -m verification.async_cancel.tokio_mir_test SCRATCH/tokio-fixed.mir` exits 0
- executed with Verus 0.2026.11.02 and Z3 4.16.0

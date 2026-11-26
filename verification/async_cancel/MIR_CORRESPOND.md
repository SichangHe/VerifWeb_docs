# Batch semaphore: compiled MIR of real Tokio vs the Verus copy
(authored by agents unless marked 🧑)

Result, 2026-11-26 UTC: for the 12 functions covered by the Verus proof ([SEMAPHORE_PROOF.md](SEMAPHORE_PROOF.md)), a script compares the compiled MIR of real Tokio `fc0d151` + [semaphore-close-fix.patch](real_tokio/semaphore-close-fix.patch) with the compiled MIR of the Verus copy. Verus erases ghost code before compiling, so the second MIR is the executable code of the file Verus verified. On every path through each function, with each basic block visited at most 3 times (also run at 5), both sides perform the same sequence of permit-relevant operations with the same symbolic arguments. 8 functions agree with no adjustment. 4 agree after one stated rewrite each, all outside the concurrent permit-moving steps. Seven mutations (four of the copy, three of the real file) behave as expected; each changed or moved atomic is caught in its own function.

This closes most of obligation 2 for the batch semaphore. The "checked by reading" step is now mechanical for these 12 functions. Its remaining trust is listed under "Trusted" below: the stub mapping, the normalisations and the loop bound.

Obligation 1 (C11 orderings): an argument below that permit conservation needs no ordering stronger than `Relaxed` at any of the 16 atomic call sites. It needs only read-modify-write atomicity and the wait-list mutex. A loom run of Tokio's batch-semaphore tests with all 16 sites weakened to `Relaxed` supports it; see "Orderings". This is an argument plus bounded testing, not a proof.

## What is compared

- inputs, both from rustc 1.91.0, the toolchain Verus pins:
  - real: `cargo rustc -p tokio --lib --features sync -- --emit=mir` on the patched checkout
  - copy: `verus --crate-type=lib batch_semaphore.rs --compile --no-verify --emit=mir`
- functions: `Semaphore::new`, `release`, `close`, `try_acquire`, `add_permits_locked`, `forget_permits`, `poll_acquire`, `Waiter::new`, `assign_permits`, `Acquire::poll`, `Acquire::new`, `Acquire::drop`
- method: symbolic execution of each MIR body over all paths
  - each path gives a trace of events
  - values are terms over parameters and earlier results, e.g. `Shl(_2, PERMIT_SHIFT)`, `load1`, `cas(compare_exchange1).Err.0`
  - locals that hold constants along a path are evaluated, so drop flags and constant `Option`s leave no branches. This is how the real code's implicit guard drops become `unlock` events
- events:
  - atomic op on a place (`_1.1` is the counter; `_4.0`, `_1.0` or `_1.0.0` is a waiter's `state`), with value arguments; orderings are recorded separately
  - `lock`, `unlock` (real: the guard is dropped; copy: explicit `unlock`; a guard dropped in the copy without `unlock` is its own event and would differ)
  - list ops (`push_front`, `last`, `pop_back`, `remove`) with the node
  - waker ops, covered-function calls, other library calls with arguments
  - stores through references, e.g. `*queued = true`
  - branches (condition, arm), asserts that can panic (condition), and the return value
- equality: the set of traces of the real function must equal the set of the copy, after the rewrites below. Paths are not filtered for feasibility; both sides include the same infeasible paths

Paths and agreement at bound 3 (bound 5: 682, 11389 and 6708 paths for `close`, `add_permits_locked`, `poll_acquire`; same verdicts):

```
Semaphore::new: real 1 paths, verus 1 paths, 1/1 distinct traces, 1 shared: equal after known rewrite(s) [0]
release: real 2 paths, verus 2 paths, 2/2 distinct traces, 2 shared: equal
close: real 42 paths, verus 42 paths, 42/42 distinct traces, 42 shared: equal
try_acquire: real 9 paths, verus 9 paths, 9/9 distinct traces, 9 shared: equal
add_permits_locked: real 193 paths, verus 193 paths, 193/193 distinct traces, 193 shared: equal after known rewrite(s) [1]
forget_permits: real 4 paths, verus 4 paths, 4/4 distinct traces, 4 shared: equal
poll_acquire: real 684 paths, verus 684 paths, 684/684 distinct traces, 684 shared: equal
Waiter::new: real 1 paths, verus 1 paths, 1/1 distinct traces, 1 shared: equal after known rewrite(s) [2]
assign_permits: real 3 paths, verus 3 paths, 3/3 distinct traces, 3 shared: equal
Acquire::poll: real 6 paths, verus 6 paths, 6/6 distinct traces, 6 shared: equal after known rewrite(s) [3]
Acquire::new: real 1 paths, verus 1 paths, 1/1 distinct traces, 1 shared: equal
Acquire::drop: real 3 paths, verus 3 paths, 3/3 distinct traces, 3 shared: equal
result: all covered functions agree up to known differences
```

## Remaining differences

Each is a rewrite of whole traces in `KNOWN` in [mir_correspond.py](semaphore_proof/mir_correspond.py). A rule that no longer fires is reported as stale, and the run fails.

0. `Semaphore::new`
   - the difference: the copy builds the wait-list mutex (a vstd `RwLock` inside a `Mutex` struct) before the counter, and also returns the ghost budget
   - why it does not matter: the initial values are the same (counter `n << 1`, empty open list), and the object is not shared during construction, so the order cannot be observed
1. `add_permits_locked`, only on the path where `rem == 0` on entry
   - the difference: real drops the guard at scope end, after `assert_eq!(rem, 0)`; the copy unlocks just before that assert
   - why it does not matter: no atomic, list or lock operation lies between the two positions, and the assert reads only a local that is 0 on this path. The path is reachable: `poll_acquire` calls `add_permits_locked(acquired, waiters)` after `assign_permits` may have used up all of `acquired`
2. `Waiter::new`
   - the difference: the intrusive-list `pointers` and `PhantomPinned` fields are absent in the copy
   - why it does not matter for the counting: `state` and `waker` are initialised identically. The missing fields are covered by the trusted list spec (obligation 3)
3. `Acquire::poll`
   - the difference: the copy's trusted `RestoreOnPending` is zero-sized, so rustc omits the move out of `Ready(coop)`
   - why it does not matter: `made_progress` is called at the same point, and the coop budget does not touch permits

## Trusted

- stub mapping: which real call and which copy stand-in name the same operation
  - real `UnsafeCell::with_mut` with the closure at line 271 or 361 = `WakerCell::take`; at line 557 = `WakerCell::register`, whose result the real closure stores into `old_waker`
  - real `Option::unwrap_or_else` with the closure at line 339 = `lock` of `self.waiters`
  - real `Acquire::project` = the four field projections
  - `trace_leaf` = `Ready(())`, which is its non-taskdump body
  - `Try::branch`/`from_residual` = the `match` that replaces `?`; `AcquireError::closed()` = `AcquireError(())`
  - `std::cmp::min` = the trusted `min`
  - `Deref`, `Pin`, `NonNull`, `Arc::{clone, deref, new}` = identity
  - the stand-ins' behaviour remains trusted as before (list, waker cell, `WakeList`, coop)
- normalisations that could hide a difference
  - references and dereferences are dropped from terms. This lets `Pin<&mut Waiter>`, `&Arc<Waiter>` and an inline `Waiter` name the same node. It would also conflate `x` with `*x` if both were used for different objects, which the types rule out here
  - the copy's vstd wrapper projections (`PAtomicUsize`, `MutexGuard.w`) are skipped
  - generic arguments and module paths are dropped from names
  - an assertion whose condition is a constant is dropped
- not compared
  - writes to locals (they matter only through later events and returns)
  - overflow-check `assert` terminators (identical debug-build checks on both sides; they can only panic)
  - unwind/cleanup paths
- bounds: each block at most 3 times per path (also run at 5). A CAS loop retried more often, or `add_permits_locked` waking more waiters than that, is not compared. Inference, not checked: the loop bodies have no state other than the loop variables. So a difference that appears only after the 4th iteration would need a body that behaves differently on later iterations
- syntactic equality of terms: stricter than semantic equivalence. It can give false alarms, but no false agreement beyond the normalisations above
- Verus's ghost erasure, and rustc producing both MIRs

## Mutations

[mutate_mir.py](semaphore_proof/mutate_mir.py) changes one side, rebuilds its MIR (copy via Verus, real via cargo), and compares against the unchanged other side. A mutation passes only if exactly the expected function differs. Run 2026-11-26 under `cpu-run LOW`:

```
original: exit 0, differing: none
verus_close_fix_unguarded: exit 1, differing: ['poll_acquire'] (caught in poll_acquire)
verus_fetch_add_unshifted: exit 1, differing: ['add_permits_locked'] (caught in add_permits_locked)
verus_close_fetch_xor: exit 1, differing: ['close'] (caught in close)
verus_drop_load_before_lock: exit 1, differing: ['Acquire::drop'] (caught in Acquire::drop)
real_master_no_close_fix: exit 1, differing: ['poll_acquire'] (caught in poll_acquire)
real_drop_load_before_lock: exit 1, differing: ['Acquire::drop'] (caught in Acquire::drop)
real_release_relaxed: exit 0, differing: none (still agrees; ordering listing changed)
```

- moved out of its branch: `verus_close_fix_unguarded` runs the close fix's `fetch_add` even when nothing was acquired. `correspond.py` cannot see this kind of change, because every line stays verbatim and in order
- changed argument: `verus_fetch_add_unshifted` gives back `rem` instead of `rem << 1`
- changed operation: `verus_close_fetch_xor` replaces `fetch_or` with `fetch_xor`
- moved across the lock and the list operation: `verus_drop_load_before_lock` and `real_drop_load_before_lock` read the waiter state before locking and unlinking
- the real file without the fix: `real_master_no_close_fix`
- ordering only: `real_release_relaxed` agrees by design, because orderings are not compared. The `--orderings` listing shows the change

## Orderings (obligation 1)

Every atomic call site in `batch_semaphore.rs` (16; `--orderings` lists the 14 in covered functions):
- counter `permits`
  - `available_permits`: `load(Acquire)`; `is_closed`: `load(Acquire)`. Neither is a covered function, and neither moves permits
  - `close`: `fetch_or(CLOSED, Release)`
  - `try_acquire`: `load(Acquire)`, then `compare_exchange(AcqRel, Acquire)`
  - `add_permits_locked`: `fetch_add(rem << 1, Release)`
  - `forget_permits`: `load(Acquire)`, then `compare_exchange_weak(AcqRel, Acquire)`
  - `poll_acquire`: `load(Acquire)`, `compare_exchange(AcqRel, Acquire)`, and the close fix's `fetch_add(acquired << 1, Release)`
- waiter `state`
  - `poll_acquire`: lock-free `load(Acquire)` when queued; `store(0, Release)` on the fast path
  - `assign_permits`: `load(Acquire)`, `compare_exchange(AcqRel, Acquire)`
  - `Acquire::drop`: `load(Acquire)`

Argument that conservation (P1) needs none of these orderings. Unchecked, by reading the code:
- every step that moves permits is one read-modify-write (RMW) on one location, between that location and the calling thread's local
  - counter: the CASes, `fetch_add`, `fetch_or`
  - waiter state: the CAS in `assign_permits`
- C11 makes every RMW read the last value in that location's modification order, at any ordering, `Relaxed` included. So each location's final value is its initial value plus the sum of its RMW deltas, and each delta has an equal and opposite change in a thread-local
- summing over locations, locals and held permits gives P1 for every execution, with no cross-location ordering needed
- the one non-RMW write that matters is `store(0)` on the fast path. It happens only when `!queued`, so the node is not linked and no other thread can reach it. The Verus proof shows "not queued ⇒ not linked"
- loads that feed a decision
  - counter loads before a CAS: a stale value only makes the CAS fail, and the failure returns the current value
  - `poll_acquire`'s early `Err(closed)` from a loaded value: `CLOSED` is only ever set, never cleared, so a value with it set means closed. On that return the call holds no permits
  - `Acquire::drop`'s and `assign_permits`' state loads: they run under the wait-list mutex, and every write to that `state` other than the unshared `store(0)` is a CAS made under the same mutex. The mutex's release/acquire makes those writes happen-before the load, so coherence gives the latest value
  - `poll_acquire`'s lock-free state load when queued: it may be stale. `state` only decreases, so a stale value is at least the current one, and the call may take more permits than still needed. The surplus stays in `acquired`. Under the mutex, `assign_permits` assigns `min(state, acquired)` and `add_permits_locked` returns the rest, or `acquired` is 0. The bounded checker ([TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md)) explores exactly these stale values and finds no loss
- so where do the orderings matter? Inference, not checked: they order the data guarded by a permit. That is the `Release` on giving permits back paired with the `Acquire`/`AcqRel` on taking them, for example the contents of `tokio::sync::Mutex<T>`. That is memory safety of clients, not counting. The wait list and waker cell are under the mutex
- what is not shown
  - a C11-level proof
  - that the Verus proof's other invariants (`inv_closed`, `inv_queue`) hold under C11; conservation does not need them
  - anything about liveness, e.g. a waiter left queued while permits sit in the counter

Loom check on the real code: Tokio's `loom_semaphore_batch` tests plus our `repoll_assign_close_conserves_permits` ([semaphore-loom.patch.rs](real_tokio/semaphore-loom.patch.rs)), with every one of the 16 sites weakened to `Relaxed`. `LOOM_MAX_PREEMPTIONS=3`, run 2026-11-26 under `cpu-run LOW`:

```
relaxed loom exit: 0
test sync::tests::loom_semaphore_batch::release_during_acquire ... ok
test sync::tests::loom_semaphore_batch::release ... ok
test sync::tests::loom_semaphore_batch::repoll_assign_close_conserves_permits ... ok
test sync::tests::loom_semaphore_batch::concurrent_permit_updates ... ok
test sync::tests::loom_semaphore_batch::batch ... ok
test sync::tests::loom_semaphore_batch::basic_closing ... ok
test sync::tests::loom_semaphore_batch::basic_usage ... ok
test sync::tests::loom_semaphore_batch::concurrent_close ... ok
test sync::tests::loom_semaphore_batch::concurrent_cancel ... ok
test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 116 filtered out; finished in 39.84s
```

Loom explores some weak-memory behaviours (stale loads within its model), not all of C11, and only these small programs. A pass is evidence for the argument, not a proof. `basic_usage` also passes. It counts concurrent holders with its own atomic, so it does not test whether data guarded by a permit is visible to the next holder; the inference about where orderings matter is not tested by this run.

## Relation to prior work

- what this is: a bounded, syntactic equivalence check between two compiled programs. It belongs to the family of translation validation (Pnueli, Siegel, Singerman, TACAS 1998) and regression verification (Godlin, Strichman, DAC 2009). Those prove equivalence for all inputs; ours compares symbolic traces up to a loop bound, with a trusted stub mapping
- what it is not
  - a refinement proof
  - Verus verifying the real file in place. That remains the stronger route in obligation 2
- earlier checks here
  - [correspond.py](semaphore_proof/correspond.py): source-line matching. It stays, as a readable map of the rewrites
  - [tokio_semaphore.py](tokio_semaphore.py): interprets the real MIR for a bounded number of futures

## Reproduce

`bash real_tokio/semaphore_mir.sh SCRATCH END VERUS` (heavy steps run under `cpu-run LOW`; delete SCRATCH afterwards). It:
- clones Tokio, checks out `fc0d151` and applies the fix
- runs `mutate_mir.py`, which builds both MIRs, compares the originals and runs the seven mutations
- prints the ordering listing
- runs the Relaxed loom tests

Single comparison: `python3 -I semaphore_proof/mir_correspond.py REAL.mir VERUS.mir [--orderings] [--bound N]`; exit 0 iff every function agrees up to the four rewrites. About 1 s at bound 3, 18 s at bound 5.

# Tokio batch-semaphore clients: Verus proof that each returns exactly the permits it holds
(authored by agents unless marked 🧑)

Result, 2026-11-20 UTC: a Verus proof, over a hand-adapted copy of the client code in which only 166 of 340 real statement lines are kept verbatim, that the covered clients of Tokio's batch semaphore return exactly the permits they hold, on drop, on cancellation (a future dropped at any suspension point), and on `close`. Each `async fn` is rewritten by hand as a future struct with `poll` and `drop`; that rewrite is checked only by reading. The covered clients are `Semaphore` and its permits, `Mutex` and its guards, `RwLock` and its guards, and bounded `mpsc`, each only for the functions listed below. Not covered, among others: the `Arc`-owning futures (`acquire_owned`, `lock_owned`, `read_owned`/`write_owned`, `reserve_owned`) and the mapped guards. Verus reports `verification results:: 177 verified, 0 errors` for the clients together with the semaphore proof. Thirteen known-bad variants each fail at the expected clause. Three of them reproduce known bugs: RwLock #2941, the effect of mpsc #8559, and the close-path leak behind the mpsc `recv` hang. Three show that the mpsc message list cannot mint permits: a double pop, a pop with no push, and a list that starts non-empty.

What was verified: a hand-adapted Verus copy of the real client code of Tokio master `fc0d151` plus [real_tokio/semaphore-close-fix.patch](real_tokio/semaphore-close-fix.patch), not a separate model: [semaphore_proof/clients.rs](semaphore_proof/clients.rs). It is checked against the real files by [semaphore_proof/correspond_clients.py](semaphore_proof/correspond_clients.py), the same method as the semaphore proof. 166 of 340 real statement lines of the 60 covered functions are kept verbatim and in order. Every added line is marked `// VERUS:` or falls in a listed category. The proof builds on the semaphore proof, so everything that proof trusts is trusted here too. It closes part of open obligation 6 of [SEMAPHORE_PROOF.md](SEMAPHORE_PROOF.md), for the covered functions only.

## Theorem

Definitions
- keyed token: a ghost token of the semaphore proof's ledger (`Sem::fl`, keyed `Key::O(id)`) with a natural-number value. Every value is counted in the ledger equation P1 of [SEMAPHORE_PROOF.md](SEMAPHORE_PROOF.md). A token cannot be duplicated or re-created for a live key, so its value can only go to 0 by moving the permits to another counted place
- client object: `SemaphorePermit`, `OwnedSemaphorePermit`, `MutexGuard`, `OwnedMutexGuard`, `MappedMutexGuard`, `RwLockReadGuard`, `RwLockWriteGuard`, `OwnedRwLockReadGuard`, `OwnedRwLockWriteGuard`, and mpsc `Permit`
- its count: `permits` for semaphore permits, 1 for mutex guards, read guards and `Permit`, `permits_acquired` for write guards
- local: a keyed token passed to a call as a ghost `&mut` argument (`op`), which must be 0 on entry and on return. It stands for permits that pass through the call's local variables
- list token: one keyed token per bounded channel, created with the channel and kept in an atomic invariant of `ListTx` (`ListPred`). Its value equals the number of values in the channel's message list

Statement (Verus-checked, per type, for sequential calls on the copy; concurrency enters only through the semaphore proof, under sequential consistency)
- type invariant: every client object owns a keyed token whose value equals its count. The type's `wf`, for example `MutexGuard::wf`, says so
- creation: a guard or permit returned by `try_*`, or by a future's `poll` as `Ready`, satisfies its invariant. Its permits are exactly those the semaphore handed out (`Acquire::poll`'s `held` token of `num_permits`, or `try_acquire`'s)
- drop: each client object's `drop` returns exactly its count to the semaphore (`release(count)` with the object's token) and ends with the token at 0
- cancellation: each hand-written future (`acquire_many`, `Mutex::lock`, `RwLock::read`/`write`, `Sender::reserve`, `Sender::send`) has a `drop` that, at any suspension point, drops the inner `Acquire`. The semaphore proof shows that `Acquire::drop` returns every permit already assigned to the future
- calls that move permits through locals return with the local at 0. These are `RwLockWriteGuard::downgrade` and its owned variant, `Permit::send`, `Sender::try_send`, `SendFuture::poll`, `Rx::recv`, `Rx::drain` and `Rx::drop`
- consumed objects: the per-type operations that end an object without its drop keep its permits. `skip_drop`/`map`, `downgrade`, `Permit::send` (permit moves into the message), `merge` and `split` move the permits to another object or local. `forget` removes them from the ledger total, as `forget_permits` does
- `Mutex` and `RwLock`: the `unreachable!()` after `acquire`/`try_acquire` is unreachable. Their semaphore is created with `close` disabled (ghost constant `closable = false`), and `close` requires `closable`. This rests on the copy containing every method of these types that could call `close`; the uncovered mapped and owned paths are not checked (a `grep` of the real `mutex.rs` and `rwlock*.rs` finds no `close` call; inference, not proof)
- bounded `mpsc`, message list: `ListTx::push` moves one permit from the sender's local into the channel's list token, and `ListRx::pop` of a value moves one permit from the list token into the receiver's local, both by the ledger's `transfer` transition. A pop of a value needs the list token at 1 or more, because the token equals the list's count. `recv` then returns the permit (`add_permit`). What is trusted is only the list's own count (see Trusted)
- bounded `mpsc`, total = bound: the channel's semaphore is created with ghost constant `fixed = true`, which forbids the transitions that change the total (`mint`, `forget`, `forget_held`). The ledger invariant `inv_fixed` gives total = initial, and `bounded::Semaphore::wf` requires `initial == bound`

Corollary for bounded `mpsc` (`recv` returns `None` after `close`). It is not one Verus theorem. The final statement:

> If the receiver has closed, and in the channel's ledger state the list token is 0, every other keyed token is 0, no queued `Acquire` future is owed permits, and no `held` permits are outstanding, then available = bound, so `is_idle()` returns true and a poll of `recv` that gets past the coop budget returns `Ready(None)`.

- Verus-checked (`lemma_channel_drained_is_idle` in `clients.rs`): for any ledger state satisfying the ledger invariants with `fixed` and `initial == bound`, the premises above, stated over the ledger's token maps (the list token by its key `ListTx::key()`), imply counter = bound
- Verus-checked: the list token's value equals the list's count (`ListPred`); total = bound for a channel (`inv_fixed`, `bounded::Semaphore::wf`); every client's contract keeps nonzero channel permits in a `Permit`, the list token, or a running call's local, and returns locals at 0
- not checked by Verus (paper): that the real situation "list empty, no `Permit` alive, no `reserve`/`send` future holding assigned permits, no call mid-flight" makes every token 0, as the premises require. The link from a token in hand to the ledger state is VerusSync's soundness argument. A Verus statement over the tokens themselves would need a judgement "these are all tokens of the instance". Verus has none, since tokens can be dropped silently
- not covered: that `recv` is polled again (wakeups; Tokio's `WakeReceiverOnDrop`, #8260, exists for that), and the `Read::Closed` path's `debug_assert!(is_idle())`, which is not proved

## Checks that the proof is not vacuous

[semaphore_proof/mutate_clients.py](semaphore_proof/mutate_clients.py) verifies the original, then thirteen variants, each with one known-bad change. A variant counts as rejected only if every Verus error is of the expected kind, in the expected file and function, at the expected clause. Run 2026-11-20 under `cpu-run LOW`, Verus `840fa612c`:

```
original: exit 0: verification results:: 177 verified, 0 errors
mpsc_recv_no_add_permit: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    postcondition in clients.rs recv: holds(*op, &self.inner.semaphore.semaphore, 0),
mpsc_permit_drop_no_release: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    postcondition in clients.rs drop: self.tok@.value() == 0,
mpsc_permit_send_then_drop: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    precondition in clients.rs send: this.drop();
mpsc_try_send_no_push: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    postcondition in clients.rs try_send: holds(*op, &self.chan.inner.semaphore.semaphore, 0),
master_no_close_fix: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    postcondition in batch_semaphore.rs poll_acquire: fl.value() == 0,
rwlock_downgrade_drops_write_guard: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    postcondition in clients.rs skip_drop: r.wf(), r.s == self.s, r.permits_acquired == self.permits_acquired,
rwlock_write_drop_releases_one: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    precondition in clients.rs drop: self.s.release(1, Tracked(self.tok.borrow_mut()), Tracked(ll::Source::
semaphore_forget_keeps_count: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    precondition in clients.rs forget: this.drop(); // VERUS: Rust drops `self` here
semaphore_merge_no_zero_other: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    precondition in clients.rs merge: other.drop(); // VERUS: Rust drops `other` here
semaphore_split_no_subtract: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    postcondition in clients.rs split: self.wf(), self.sem == old(self).sem,
    postcondition in clients.rs split: Some(p) ==> p.wf() && p.sem == self.sem && p.permits == n && self.perm
mpsc_list_double_pop: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    invariant in clients.rs pop: open_atomic_invariant!(tx.inv.borrow() => g => {
mpsc_list_pop_without_push: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    precondition in clients.rs pop: move_permits(tx.sem_inst.borrow(), &mut tok, op, 1);
mpsc_list_starts_nonempty: exit 1: verification results:: 176 verified, 1 errors (rejected as expected)
    precondition in clients.rs list_channel: AtomicInvariant::new((sem.inst@.id(), raw_tx.id(), tok.key()->O_0), (l
```

Known bugs among them
- `master_no_close_fix`: the close-path leak on master ([TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md)), checked here together with all clients. It fails in `poll_acquire`, as in the semaphore proof. By the corollary's argument, this leak is what keeps a closed, drained channel from becoming idle, which is the `recv` hang reproduced in loom. The proof rejects the cause. It does not separately derive the hang
- `rwlock_downgrade_drops_write_guard`: tokio-rs/tokio#2941, fixed by #2957 (`e804f88d`). Its commit message, verbatim: "When `RwLockWriteGuard::drop` gets invoked however another `MAX_READS` permits are added. This results in releasing more permits that were actually aquired when downgrading a write to a read lock." The variant lets the write guard's drop run inside `skip_drop` (no `ManuallyDrop`)
- `mpsc_permit_send_then_drop`: the effect of tokio-rs/tokio#8559, fixed by #8560 (`5b758f5b`). Its commit message, verbatim: "a panic in the receiver's `Waker::wake` implementation causes unwinding to drop `Permit` after the value has already been enqueued. Dropping `Permit` returns a permit to the semaphore, and receiving the enqueued message returns the permit a second time". The variant runs the `Permit`'s drop after enqueueing on every call. The real bug happens only on unwind, which is out of scope, so the pre-#8560 statement order (`send` before `mem::forget`) is not itself rejected
- the three `mpsc_list_*` variants weaken the trusted list spec: a popped value stays counted (double pop; fails restoring `ListPred` in `ListRx::pop`), a pop may return a value from an empty list (pop with no push; fails `move_permits`'s `k <= from.value()`), and a new list starts with one value (fails creating the invariant). So the verified code relies on the list count, and the list cannot mint permits without breaking it
- the other seven are synthetic: a leak or a double release in one statement

## How the proof is tied to the real code

[semaphore_proof/correspond_clients.py](semaphore_proof/correspond_clients.py) reuses `correspond.py`'s normalisation and ghost erasure:
- input: 60 entries. Each maps one or more real functions (bodies concatenated in order) to one Verus function. An `async fn` maps to the `poll` of its hand-written future. Example: `Mutex::acquire` + `Mutex::lock` map to `LockFuture::poll`
- the real side also drops compiled-in `#[cfg(not(all(tokio_unstable, ..)))]` and `#[allow(..)]` attribute lines. It expands `macro_rules! try_recv` at its two uses, as rustc does
- result: 166 of 340 real lines kept verbatim in order; 174 changed. 204 added lines: 167 marked, 37 in allowed categories, 0 unexplained (re-run after the list-token change: same counts)
- per file: `semaphore.rs` 40/61 kept (17 entries); `mutex.rs` 24/41 (9); `rwlock.rs` + `rwlock/*.rs` 42/94 (13); `mpsc/chan.rs` + `mpsc/bounded.rs` 60/144 (21)
- the kept fraction is lower than the semaphore's (116/215) because `async fn` bodies are rewritten as `poll` functions. Every line of an `async` body that awaits, and every guard construction that carried tracing fields, counts as changed

Categories of rewritten lines (each `// VERUS:` marker names its own)
- `async fn` written as a future struct with `poll` and `drop`, with nested `async` blocks flattened. The `.await` becomes: create the `Acquire` on the first poll, poll it, keep it while `Pending`, drop it when `Ready`. Locals live across the await (`WakeReceiverOnDrop`'s `guard`, `send`'s `value`) become fields
- `impl Drop` becomes a method `drop`. Implicit drops (`other` in `merge`, `self` in `forget`, `guard` on the error path) are explicit calls. `mem::ManuallyDrop::new(self)` and `mem::forget` become "no `drop` call follows"
- ghost fields `tok` on client objects, and a ghost `op` argument on calls that move permits through locals
- `unwrap_or_else(|_| unreachable!())` becomes a `match` with `unreachable_()`, whose precondition is `false`, so Verus must prove the arm unreachable. `assert!` on caller input becomes the trusted `check`; `debug_assert_ne!(self.mr, 0)` becomes `runtime_assert` (proved)
- `mut self` and `mut` parameters become locals; `x -= n` on a field becomes `x = x - n`
- `rx_fields.with_mut(|..| ..)` is inlined, with `rx_fields` moved from `Chan`'s `UnsafeCell` into `Rx`, the only accessor. The closure's early `return` leaves only the closure; it is written as `if .. {} else {..}`
- `chan.rs` is specialised to `S = bounded::Semaphore`; the `chan::Semaphore` trait methods are inherent methods
- omitted fields and code that do not touch permits: protected data (`UnsafeCell<T>`, `data` pointers, `PhantomData`), `map` closures, tracing spans and `trace::async_op`, `tx_count`/`tx_weak_count`, `CachePadded`

Not mechanically checked (as for the semaphore): that trusted stand-ins behave as specified, that each rewrite preserves meaning, and that a kept line stays in its branch. The desugaring of `async fn` is the largest rewrite and is checked only by reading.

## Ghost-only changes to the semaphore proof

`batch_semaphore.rs` changed only in ghost code and contracts. `correspond.py` reports the same `116/215` and `added: 97 (56 marked, 41 allowed, 0 unexplained)` as before; `mutate.py` rejects the same five variants for the same reasons.
- `Sem` constant `closable`. `Semaphore::new` takes it as a ghost argument, and `close` requires it. New invariant: an unclosable semaphore is never closed. New contracts: `poll_acquire`, `Acquire::poll` and `try_acquire` return a closed error only if `closable`
- `Sem` constants `fixed` and `initial`. `Semaphore::new` takes `fixed` as a ghost argument. `mint`, `forget` and `forget_held` require `!fixed`, so `release` of new permits and `forget_permits` require it too. New invariant `inv_fixed`: `fixed ==> total == initial`
- transition `transfer`: move permits between two keyed `O` tokens. Transition `forget_held`: a keyed `O` token gives up permits, and total drops by the same amount
- `release` accepts `Source::Stashed`: the permits are already in the `op` token
- the P1 equation is unchanged; its "forgotten" term now also counts `SemaphorePermit::forget`
- Verus: `94 verified, 0 errors` for `batch_semaphore.rs` alone (was 88; invariants are not counted); the five mutations report `93 verified, 1 errors` each

## Trusted (in addition to the semaphore proof's list)

- the rewrites above, in particular:
  - the `async` desugaring matches rustc's coroutine lowering: which locals are live at each suspension point, and drop order. `reserve_inner` drops the `Acquire` before `guard`
  - moving a pinned `Acquire` out of and back into the future's `Option` inside `poll` is harmless (true for the `Arc`-node copy; the real future is pinned)
- Rust runs each `drop` exactly once with the type invariant holding, and never for a value passed to `mem::forget`/`ManuallyDrop`
- the bounded-mpsc block list (`RawTx::push`, `RawRx::pop`, `raw_channel`), only through a ghost count `ListLen` of its values: a new list has count 0, `push` adds 1, and a `pop` that returns a value needs count ≥ 1 and subtracts 1. These are linearizable (`#[verifier::atomic]`), open no invariant and do not unwind. The spec says nothing about permits; the permit movement is verified
- `AtomicWaker`, `Notify`, `poll_proceed`: no effect on permits
- `check` (input `assert!`s panic iff false), `ptr_eq`/`arc_ptr_eq` (equal addresses mean the same semaphore), and `unreachable_` (trusted to panic, but Verus proves it unreachable)
- Verus tokens can be dropped silently. Within a function body, the proof rests on contracts: every token is an object field with an invariant, a `&mut` argument with an `ensures`, or a return value. A ghost local holding permits and dropped inside a body would not be caught; we checked by reading that there is none
- client obligations: `channel(buffer)` requires `buffer <= MAX_PERMITS` (larger values panic in `Semaphore::new`); `Semaphore::add_permits` called by users still needs the ghost budget

## Not covered

Blocked, with the reason
- the `Arc`-owning futures, which are not covered at all (`acquire_owned`/`acquire_many_owned`, `Mutex::lock_owned`, `RwLock::read_owned`/`write_owned`, `Sender::reserve_owned`): the coroutine moves an `Arc` into itself and an `Acquire` borrows from it. That struct is self-referential, which Verus struct lifetimes cannot express. The owned guards and permits they return are covered (drop, `forget`/`merge`/`split`, owned write `downgrade`), and the `try_*_owned` constructors are covered
- unwinding: #8559 itself (a panicking waker during `Permit::send`), #8541/#8542, and any `assert!`/`check` failure. Verus has no unwind semantics for exec code
- the paper step of the mpsc corollary, and liveness (wakeups): see Theorem

Not attempted (no blocker known; same patterns as the covered code)
- `Semaphore::acquire`/`try_acquire`/`acquire_owned` with `n = 1`: same bodies as the covered `_many` versions with `1`, but not checked separately
- `blocking_*` variants; `PollSemaphore`
- `MutexGuard::try_map`, `OwnedMutexGuard::map`/`try_map`, `OwnedMappedMutexGuard`; `RwLock` mapped guards, `map`/`try_map`/`downgrade_map`/`try_downgrade_map`/`into_mapped`
- mpsc: `reserve_many`/`PermitIterator`, `try_reserve*`, `OwnedPermit` (`send`, `release`), `send_timeout`, `recv_many`, `try_recv`, `Sender::closed`, `WeakSender`, `Chan::drop`, and the unbounded channel

## Prior work, and what is new

- Tokio's own checks of these clients over the real code
  - loom: `loom_mpsc.rs` (e.g. `closing_bounded_rx`, `closing_and_sending`, `try_recv`), `loom_rwlock.rs` (`concurrent_write`, `concurrent_read_write`, `downgrade`), `loom_semaphore_batch.rs`. These are fixed small programs, bounded by preemptions
  - integration tests: e.g. `tests/sync_mpsc.rs` `recv_close_gets_none_reserved`, `cancelled_reserve_wakes_closed_receiver`, `ready_close_cancel_bounded`; `tests/sync_rwlock.rs` `downgrade_map`; `tests/sync_mutex.rs` `mutex_coop_drop_after_take_permit`
  - the earlier reading of the 8 loom semaphore tests found none that re-polls a queued waiter and closes in the window that leaks ([TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md)); our added loom tests do. The mpsc integration tests were not checked for this window
- verification: Lion verifies its own runtime; Li et al. evaluate Tokio's oneshot and name "tokio's Mutex, Semaphore" as a gap; CQS verifies a Kotlin semaphore. See [SEMAPHORE_PROOF.md](SEMAPHORE_PROOF.md) for quotes. We know of no proof about Tokio's `Mutex`, `RwLock` or `mpsc`. This rests on the 2026-11-18 search, not exhaustive; no new search was done for this step
- Joshi et al. (SOSP '26) inject task drops in application code that runs over re-implemented Tokio primitives. That is testing, and not of these primitives
- new here
  - a Verus proof over a source-checked copy of the real client code that each covered client type returns exactly its permits on drop, cancellation and close. The client contracts are about sequential calls (`&mut`); any number of threads and objects is covered only through the semaphore proof, under sequential consistency
  - `Mutex`/`RwLock` never reach their `unreachable!()`, for the covered methods
  - the bounded-mpsc message list moves permits by ledger transitions, so it cannot mint them
  - the channel-level corollary that a drained, closed bounded channel is idle: the ledger step is a Verus lemma, the step from "drained" to "all tokens 0" is on paper
  - #2941 and the effect of #8559 rejected as mutations

## Must not claim

- "verified Tokio's sync primitives" or "Tokio's sync primitives are cancel safe" without qualification. Say: "a Verus proof, for a hand-adapted copy of Tokio's semaphore clients (master `fc0d151` + close fix; 166 of 340 real lines of 60 covered functions kept verbatim; `async fn`s rewritten as hand-written futures), that each covered client type returns exactly the permits it holds on drop, cancellation and close, under the semaphore proof's assumptions (sequential consistency, a trusted list spec, `Drop` run once) plus a trusted count of the mpsc message list"
- that master as shipped is correct: it fails (`master_no_close_fix`)
- that `recv` returns `None` as a single Verus theorem: the step from "drained" to "all tokens 0" is on paper, and wakeups are not covered
- anything about the types listed under Not covered, unwinding, liveness, or memory safety

## Reproduce

From `verification/async_cancel/semaphore_proof/`, with `VERUS` the Verus binary (`verus-lang/verus` `840fa612c`):
- `$VERUS --crate-type=lib clients.rs` (the crate includes `batch_semaphore.rs`) → `verification results:: 177 verified, 0 errors` (about 10 s)
- `python3 -I mutate_clients.py $VERUS` → the output above; exit 0
- correspondence: check out Tokio `fc0d151753b5fb10125ecef2d48f29b192c9abcf` in a scratch dir and apply `real_tokio/semaphore-close-fix.patch`. Then `python3 -I correspond_clients.py SCRATCH/tokio/tokio/src/sync` → `total: 166/340 real lines kept verbatim in order; 174 changed (60 entries)` and `added: 204 (167 marked, 37 allowed, 0 unexplained)`; exit 0

# Tokio batch semaphore: unbounded Verus proof of permit conservation
(authored by agents unless marked 🧑)

Result, 2026-11-20 UTC: a Verus proof that Tokio's batch semaphore conserves permits under cancellation and `close`, for any number of futures, permits and threads, and any interleaving. It covers master `fc0d151` plus the candidate fix [real_tokio/semaphore-close-fix.patch](real_tokio/semaphore-close-fix.patch). Verus reports `verification results:: 94 verified, 0 errors` (88 before the ghost-only additions made for the clients; see below). Master without the fix fails the proof. So do four other known-bad variants, each for its expected reason.

Follow-up, 2026-11-20: for a hand-adapted copy of Tokio's clients of this semaphore (`Semaphore` and its permits, `Mutex`, `RwLock`, bounded `mpsc`; 166 of 340 real lines kept verbatim, each `async fn` rewritten by hand as a future and checked only by reading), Verus checks that the covered functions return exactly the permits they hold on drop, cancellation and close: [CLIENTS_PROOF.md](CLIENTS_PROOF.md). The `Arc`-owning futures (`acquire_owned`, `lock_owned`, `read_owned`/`write_owned`, `reserve_owned`) and the mapped guards are not covered. This closes part of obligation 6 below.

What was verified: a hand-adapted Verus copy of the real `batch_semaphore.rs`, not a separate model. Of the 215 statement lines of the 12 covered real functions, 116 are kept verbatim and in order. The rest are rewritten in the categories listed under "How the proof is tied to the real code", including `Pin`/`NonNull` and the intrusive list replaced by `Arc` plus a trusted-spec list, and `Drop` made a plain method. The copy keeps the real atomic operations; every line it adds carries a `// VERUS:` marker or falls in a listed category (checked by `correspond.py`). The linked list, wakers, coop budget and std types have trusted specifications. The mutex is vstd's verified `RwLock`. The proof is in [semaphore_proof/batch_semaphore.rs](semaphore_proof/batch_semaphore.rs).

## Theorem

Definitions
- `S`: a semaphore created by `Semaphore::new(n)`, with two ghost constants chosen at creation: `closable` (whether `close` may be called) and `fixed` (whether the total may change)
- available: `S.permits >> 1`, the counter word without the `CLOSED` bit
- queued future: a live `Acquire` future `f` whose `f.queued` flag is set. Its owed permits are `f.num_permits − f.node.state`: the permits already assigned to it
- local permits: the value of a running call's local variable that holds permits taken from the counter or a waiter. These are `acquired` in `poll_acquire` and `rem` in `add_permits_locked`
- held: permits handed to callers. These are an `Acquire` that returned `Ready(Ok)` and a successful `try_acquire`, and they are not yet `release`d
- total: `n` + permits added by `release` as new permits − permits removed by `forget_permits` or by a permit's `forget` (ghost transition `forget_held`, added for the clients). If `fixed`, total = `n` always (invariant `inv_fixed`)

Statement (P1, conservation). The following holds in every reachable state of every execution. It holds for any number of threads and `Acquire` futures, with `poll`, `drop`, `release`, `close`, `try_acquire` and `forget_permits` interleaved in any order at atomic-operation granularity, subject to their preconditions: `close` requires `closable`; `release` of new permits and `forget_permits` require `!fixed`:

  available + Σ over queued futures of owed + Σ over running calls of local + held = total

Every call also returns with its local permits at 0. A call cannot leave permits in a local that dies with it.

Also proved
- if `!closable`, the semaphore is never closed, so `poll_acquire`, `Acquire::poll` and `try_acquire` never return a closed error
- a future that completed (`Ready(Ok)` handed its permits to the caller) or that was dropped is never in the wait list. This is the property the intrusive list needs to avoid dangling pointers. Memory safety itself is not proved
- every `assert!`/`assert_eq!` in the covered functions holds. That includes `prev + permits <= MAX_PERMITS` in `add_permits_locked`, so the "would overflow" panic cannot fire when new permits come only from the budget (below)
- drop of a future that is not queued touches nothing; drop of a queued future returns exactly its owed permits
- `forget_permits(n)` returns `r` with `r <= n` (an `ensures`). That `r` equals the amount removed from the ledger is proved by an `assert` inside the successful CAS's ghost step, not by an `ensures`: the ledger lives in shared ghost state, and the function has no per-call token through which a postcondition could name the removed amount

Client obligations (preconditions; the theorem is about clients that meet them)
- a future is not polled after it returned `Ready(Ok)`. The `Future` contract leaves that unspecified
- `release(k)` takes a ghost token for `k` held permits, or `k` units of a budget for new permits. The budget is created by `new` as `MAX_PERMITS − n`. So callers never release permits they do not have, and never exceed `MAX_PERMITS`
- Rust runs `Acquire::drop` once when the future is dropped (see trusted assumptions)
- `close` only on a `closable` semaphore; new permits and `forget_permits` only on a non-`fixed` one
- `held` and `budget` are ghost tokens, so these obligations are not enforced on real Rust callers. In particular, overflow freedom of `release` relies on clients staying within the budget
- discharged for Tokio's own clients, as far as covered, in [CLIENTS_PROOF.md](CLIENTS_PROOF.md): each client object keeps its permits in a keyed ledger token and releases exactly that token (`Source::Stashed`)

How the proof is organised
- a VerusSync tokenized state machine `Sem` ([batch_semaphore.rs](semaphore_proof/batch_semaphore.rs), first half) holds the ghost ledger. Its fields are:
  - the counter (`counter`)
  - the wait list (`lk`)
  - each waiter's `state` (`ws`)
  - each future's phase (`own`: `Idle`, `Fast`, `Reg`, `Done`)
  - locals (`fl`), held permits (`held`), the budget (`budget`) and `total`
- invariants
  - `inv_ledger` is P1
  - `inv_closed`: if the list is open and non-empty, the counter is 0
  - `inv_queue`: every linked waiter is registered, has `state > 0`, and has no local permits while open
  - `inv_fixed`: if `fixed`, total = initial
  - Verus checks that the initial state satisfies them and that all 22 transitions preserve them (20 before 2026-11-20; `transfer` and `forget_held` were added for the clients, together with the constants `closable`, which `close` requires, and `fixed`/`initial`, where `fixed` forbids `mint`, `forget` and `forget_held`)
- each atomic's ghost invariant ties the real value to its token
  - the counter word: `v == 2·permits + closed`
  - each waiter: `state == ws.state`
  - so the ledger equation is about the real atomics, not copies of them
- each executable function's ghost code performs exactly one transition per real atomic step, inside that step's `atomic_with_ghost!`. One local per call is a map token keyed by the call. Its contract requires it to come back at 0. Verus tokens may be dropped silently, but a token cannot be re-minted for a key the ledger still has. So the only way to satisfy the contract is to move the permits somewhere the ledger counts
- why the close fix is needed: on the `waiters.closed` early return, `acquired` permits sit in the local. Without the fix, `poll_acquire`'s postcondition `fl.value() == 0` fails

## Checks that the proof is not vacuous

[semaphore_proof/mutate.py](semaphore_proof/mutate.py) verifies the original, then five variants, each with one known bug. "Master" (`master_no_close_fix`) means the Verus copy with the close-fix block removed; it is not the real master file. A variant counts as rejected only if every Verus error is of the expected kind, in the expected function, at the expected clause (the script reads the line and column Verus reports). Run 2026-11-20 under `cpu-run LOW`, Verus `840fa612c` (2025-11-30 build); re-run after the ghost-only client additions, same verdicts:

```
original: exit 0: verification results:: 94 verified, 0 errors
master_no_close_fix: exit 1: verification results:: 93 verified, 1 errors (rejected as expected)
    postcondition in poll_acquire: fl.value() == 0,
pre8542_fast_path: exit 1: verification results:: 93 verified, 1 errors (rejected as expected)
    postcondition in poll_acquire: fl.value() == 0,
    postcondition in poll_acquire: Poll::Ready(Ok(_)) ==> own.value() == Own::Fast,
drop_no_return: exit 1: verification results:: 93 verified, 1 errors (rejected as expected)
    postcondition in drop: self.fl@.value() == 0,
drop_no_remove: exit 1: verification results:: 93 verified, 1 errors (rejected as expected)
    precondition in drop: self.semaphore.inst.borrow().retire(self.node.id@, &mut lk, &g, to, tf
poll_clear_on_pending: exit 1: verification results:: 93 verified, 1 errors (rejected as expected)
    postcondition in poll: self.wf(), self.id() == old(self).id(), self.semaphore == old(self).se
```

Expected reasons, as checked:
- `master_no_close_fix` and `pre8542_fast_path`: `poll_acquire` postcondition `fl.value() == 0`. The permits are still in the local when the call returns. `pre8542_fast_path` may also fail `ret matches Poll::Ready(Ok(_)) ==> own.value() == Own::Fast` at the same return
- `drop_no_return`: `Acquire::drop` postcondition `self.fl@.value() == 0`
- `drop_no_remove`: the precondition of the `retire` transition. That transition requires the waiter to be off the list
- `poll_clear_on_pending`: `Acquire::poll` postcondition `self.wf()`. `queued` no longer matches the future's phase

The bounded checker ([TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md)) rejects the same four drop and fast-path mutations. It also finds the `close` leak on master.

## How the proof is tied to the real code

The Verus file is a hand-adapted copy of the real source: ghost code added, and executable lines rewritten in the categories below.

[semaphore_proof/correspond.py](semaphore_proof/correspond.py) checks this mechanically, function by function:
- input: 12 functions of the real file (master + fix; comments and `#[cfg(all(tokio_unstable, ..))]` tracing items removed): `Semaphore::new`, `release`, `close`, `try_acquire`, `add_permits_locked`, `forget_permits`, `poll_acquire`, `Waiter::new`, `assign_permits`, `Acquire::poll`, `Acquire::new`, `Acquire::drop`
- method: erase ghost syntax (`proof` blocks, `open_atomic_invariant!`, tracked/ghost lets, `Tracked`/`Ghost` arguments and fields, loop invariants), turn `atomic_with_ghost!(&x => op(args); ..)` back into `x.op(args)`, drop memory-ordering arguments, read `waiters.w.f` as `waiters.f`
- check 1, kept: each real line that appears verbatim in the Verus function, in order. Result: 116 of 215 kept; the other 99 are printed as changed. For the nine functions covered before 2026-11-20 this is 110 of 186 (the earlier script reported 100 of 186; the gain comes from the more complete ghost erasure, e.g. reading `waiters.w.f` as `waiters.f` and erasing loop invariants, not from code changes)
- check 2, added: each Verus executable line not matched to a real line must carry a `// VERUS:` marker (on the line or on a comment-only line directly above) or match an `ALLOWED` category in the script; otherwise the script exits 1. Result: 97 added lines: 56 marked, 41 in allowed categories, 0 unexplained
- check 2 found one unmarked addition, now removed: an extra atomic `node.state.load()` in the `!*queued` branch of `poll_acquire`, used only to obtain the ghost fact `num_permits <= MAX_PERMITS`. Real Tokio has no such load. That fact is now a precondition of `poll_acquire` and part of `Acquire::wf`, established by `Acquire::new`'s `assert!`

Categories of rewritten lines (each `// VERUS:` marker names its own):
- `MutexGuard` is explicit:
  - `waiters.closed` becomes `waiters.w.closed`
  - every lock acquisition also returns the ghost wait-list token, so the guard is bound to a name where the real code uses `self.waiters.lock()` inline
  - each implicit guard drop is an explicit `unlock`, including the drops on early returns. Rust drops guards implicitly; Verus has no verified `Drop` for guards
  - `Mutex::new(Waitlist { .. })` is built as a vstd `RwLock` holding the list and its ghost token
- `assert!`/`assert_eq!` become `runtime_assert(cond)`. It is trusted to panic exactly when `cond` is false; Verus proves `cond`
- control-flow sugar Verus does not accept, rewritten to its expansion:
  - `break value` from `loop`: kept in an `Option`
  - `while c { let Some(x) = .. else { break } }`: written as `loop { if !c { break } match .. }`
  - `let .. else`, `r?`, `ready!(..)`, `unwrap_or_else(|| ..)`: written as a `match`
  - `cmp::min`: a trusted `min`
  - an atomic call's result is bound to a name (`res`, `s`, `st`) before its use, so the ghost step can see it
  - a `mut` parameter becomes a local; `AcquireError::closed()` is inlined as `AcquireError(())`
- intrusive pointers
  - `Pin<&mut Waiter>`/`NonNull<Waiter>` become `Arc<Waiter>`; `Acquire.node` is an `Arc<Waiter>`
  - `queue.remove(NonNull::from(&mut self.node))` becomes `queue.remove(&self.node)`; `push_front` takes `node.clone()`
  - `project()` is inlined as field accesses
- `waker.with_mut(|w| ..)` becomes the trusted `WakerCell::take`/`register`
- tracing and taskdump code (`trace_leaf`, `trace_poll_op!`, spans) is removed
- the `Pointers` and `PhantomPinned` fields of `Waiter` are removed; the trusted list replaces them
- `impl Drop for Acquire` becomes a plain method `Acquire::drop` (see trusted)

Not mechanically checked: that the trusted stand-ins behave as specified, that each rewrite preserves meaning, and that no real line was moved into a different branch. The in-order check does not detect a line moved to another branch; the mutation results and a manual read are the evidence for that. The `ALLOWED` categories are regexes on single lines; a line that matches one is not inspected further.

## Trusted (not proved)

- the real source is reduced to this copy by the changes listed above. The checker shows which lines changed, not that each change preserves meaning
- Verus, Z3 and rustc; VerusSync's macro-generated token rules (vstd says the macro "creates trusted implementations")
- memory model: Verus treats every atomic operation as one sequentially consistent step and ignores `Ordering`. The real code uses `Acquire`/`Release`/`AcqRel`. The bounded checker covered stale waiter-state loads; this proof does not. A C11-level argument is not done (see what remains)
- the intrusive `LinkedList` spec: `push_front`, `last`, `pop_back`, `remove`
  - as a sequence of `Arc<Waiter>`, with nodes identified by a ghost id instead of an address
  - `remove` is assumed to remove exactly the node with that id, given no duplicates; the proof shows there are none
  - assumed: one node per future, at a stable address, i.e. pinning works
- the waker cell, `WakeList`, `poll_proceed`/`RestoreOnPending`, and `Poll::is_ready`/`mem::drop` specs. All are assumed not to touch permits. `poll_proceed` may return `Pending` at any poll, which the proof handles
- `Acquire::drop` is verified as an ordinary method. Rust's `Drop::drop` runs it exactly once when the future is dropped, with the type invariant `Acquire::wf` holding. Verus cannot verify a `Drop` impl with a precondition (see [REPORT.md](REPORT.md), Drop section)
- `runtime_assert`, `min`: trivial trusted wrappers
- usize is 64-bit (`global size_of usize == 8`)

## Out of scope

- unwinding: the #8542 tracing-panic path is not compiled; panics in wakers and in a tracing subscriber
- liveness: a waiter is eventually woken; `close` terminates; CAS loops terminate (loops carry no `decreases`)
- the other `Semaphore` entry points (`acquire_many`, `Semaphore::add_permits` wrappers in `semaphore.rs`, `SemaphorePermit`'s `Drop`), `Mutex`, `RwLock` and `mpsc` on top. Their correct use of `release` is a client obligation here; for the functions covered there, it is checked in [CLIENTS_PROOF.md](CLIENTS_PROOF.md)
- polling a future after `Ready(Ok)`

## Relation to prior and our own work

- our bounded checker ([TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md))
  - it interprets the compiled MIR for ≤ 3 futures and ≤ 4 permits, with stale waiter-state loads
  - this proof is unbounded and covers `close`
  - but it works on a source copy, not on MIR, and assumes sequential consistency
  - the two agree: both reject the same mutations, and the close leak on master
- loom (Tokio's 8 tests and our two added loom tests) runs fixed small programs on the real code, bounded by preemptions. It is evidence about the real compiled code, including some weak-memory behaviour within loom's model. The proof is not
- Lion (SOSP '26, [LION.md](LION.md))
  - it verifies its own runtime's waiter kernel, `remove_step`: "exact permit accounting, and a verified cancellation step"
  - its cancellation glue (`Notified::drop`) is trusted
  - we verify Tokio's own drop path and the `poll_acquire`/`add_permits_locked` interleavings against concurrent atomics
  - Lion's kernel is a sequential step function, not lock-free code
- CQS (Koval, Khalanskiy, Alistarh, [arXiv:2111.12682](https://arxiv.org/abs/2111.12682))
  - a formally verified fair, abortable semaphore and queue for Kotlin coroutines; a different algorithm and language
  - this is the closest verified cancellable semaphore
  - we do not claim the first verified cancellable semaphore. We found no prior proof of Tokio's semaphore (search of 2026-11-18, not exhaustive)
- Joshi et al., "Validating a High-Performance Cloud Object Store with Lightweight Formal Methods", SOSP '26, [doi:10.1145/3830418.3843899](https://doi.org/10.1145/3830418.3843899). Read in full (PDF), 2026-11-20
  - they test cancellation safety of application code (S3 Express) by injecting drops in the Shuttle stateless model checker, page 700: "We also extended our test framework to inject task drops at intermediate await points (to check cancellation safety) and to inject timeouts on demand"
  - page 700, their notion: "operations must satisfy cancellation safety: they should be correct even when dropped mid-update"
  - they re-implemented Tokio's primitives for Shuttle, page 700: "Shuttle did not support Tokio when we started, so we reimplemented Tokio's concurrency primitives so they can be controlled by the Shuttle runtime." So their checking runs against stand-ins for Tokio's primitives, not against Tokio's semaphore
  - it is testing: sampled schedules, bounded programs
  - their bug is the same class as ours, page 702: "The fix was to implement a Drop guard that clears the pending_reads entry when the future is dropped, restoring cancellation safety"
  - difference: they find bugs in application code by injection; we prove a stated resource invariant of a library for all schedules and sizes, under stated trust
- Li, Beschastnikh, Summers ([arXiv:2610.09198](https://arxiv.org/abs/2610.09198)) list Tokio's Semaphore as a gap ("a wake-one primitive ... (e.g., tokio's Mutex, Semaphore)") and prove liveness, which we do not

## What remains: obligations for a later effort

1. Memory model: prove P1 under C11 orderings. Candidates:
   - a relaxed-memory logic, e.g. an Iris-based RustBelt-relaxed or GPS-style proof
   - an argument that every load feeding a decision is either a CAS input (a stale value only makes the CAS fail) or protected by the mutex's happens-before. The checker's note in [TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md) sketches this; it is unchecked
2. Real-code link at MIR level: show that the Verus copy's executable statements equal the compiled MIR of `fc0d151`+fix. Two possible routes:
   - extend `tokio_semaphore.py`'s MIR parser to produce the same normalised statements as `correspond.py`
   - verify the real file in place with Verus attributes. That needs Verus support for `Pin`, implicit guard drops, `let .. else`, `?` in `Poll`, `break` with value, and closures in `unwrap_or_else`/`with_mut`
3. The intrusive list: replace the trusted `LinkedList` spec with a verified one over raw pointers (e.g. vstd `PPtr`/`PointsTo`). That also needs proofs that the waiter's address is stable (pinning) and that `Waiter` is freed only after it is unlinked. The ghost invariant "done ⇒ unlinked" is already proved
4. `Drop`: get Verus to verify `impl Drop for Acquire` with the type invariant, or prove that Rust calls it once. Today Verus requires `Drop` to have no precondition and `opens_invariants none` ([REPORT.md](REPORT.md))
5. Unwinding: the tracing-panic paths (#8541, #8542) need an unwind-aware semantics; Verus has none for exec code
6. Clients: prove that `SemaphorePermit::drop`, `Mutex`, `RwLock` and bounded `mpsc` call `release` with exactly the held permits. This is the step to "Tokio's sync primitives conserve permits under cancellation". It also covers the bounded-`mpsc` `recv` hang ([TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md))
   - partly done 2026-11-20, [CLIENTS_PROOF.md](CLIENTS_PROOF.md), for a hand-adapted copy (166 of 340 real lines kept; `async fn`s rewritten by hand). Remaining: the `Arc`-owning futures (self-referential coroutines, not expressible as Verus structs), the mapped guards and other types listed there as not attempted, a check of the `async` rewrite, and the paper step of the `mpsc` corollary
7. Liveness (waiters are eventually woken), in the style of Lion or Li et al.

## Must not claim

- "verified Tokio's semaphore" without qualification. Say "a Verus proof of permit conservation for a hand-adapted Verus copy of Tokio's `batch_semaphore.rs` (master `fc0d151` + close fix; 116 of 215 real lines of the covered functions kept verbatim, the rest rewritten in listed categories, including `Pin`/`NonNull` and the intrusive list replaced by `Arc` plus a trusted-spec list, and `Drop` made a plain method), assuming sequential consistency and a trusted list spec, for clients that respect the ghost `held`/budget obligations"
- anything about master as shipped, beyond this: the proof fails there, consistent with the leak reproduced in loom
- liveness, unwind safety, or memory safety

## Reproduce

From `verification/async_cancel/semaphore_proof/`, with `VERUS` the Verus binary (built from `verus-lang/verus` `840fa612c`):
- `$VERUS --crate-type=lib batch_semaphore.rs` → `verification results:: 94 verified, 0 errors` (about 5 s)
- `python3 -I mutate.py $VERUS` → the output above; exit 0
- correspondence:
  - clone Tokio into a scratch dir
  - `git checkout fc0d151753b5fb10125ecef2d48f29b192c9abcf && git apply .../real_tokio/semaphore-close-fix.patch`
  - `python3 -I correspond.py SCRATCH/tokio/src/sync/batch_semaphore.rs` → per-function counts, then `total: 116/215 real lines kept verbatim in order; 99 changed` and `added: 97 (56 marked, 41 allowed, 0 unexplained)`; exit 0

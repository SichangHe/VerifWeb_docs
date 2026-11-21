# Tokio batch semaphore: unbounded Verus proof of permit conservation
(authored by agents unless marked 🧑)

Result, 2026-11-20 UTC: a Verus proof that Tokio's batch semaphore conserves permits under cancellation and `close`, for any number of futures, permits and threads, and any interleaving. It covers master `fc0d151` plus the candidate fix [real_tokio/semaphore-close-fix.patch](real_tokio/semaphore-close-fix.patch). Verus reports `verification results:: 88 verified, 0 errors`. Master without the fix fails the proof. So do four other known-bad variants.

What was verified: a minimally changed copy of the real `batch_semaphore.rs`, not a separate model. It keeps the real control flow, arithmetic and atomic operations. The linked list, wakers, coop budget and std types have trusted specifications. The mutex is vstd's verified `RwLock`. The proof is in [semaphore_proof/batch_semaphore.rs](semaphore_proof/batch_semaphore.rs).

## Theorem

Definitions
- `S`: a semaphore created by `Semaphore::new(n)`
- available: `S.permits >> 1`, the counter word without the `CLOSED` bit
- queued future: a live `Acquire` future `f` whose `f.queued` flag is set. Its owed permits are `f.num_permits − f.node.state`: the permits already assigned to it
- local permits: the value of a running call's local variable that holds permits taken from the counter or a waiter. These are `acquired` in `poll_acquire` and `rem` in `add_permits_locked`
- held: permits handed to callers. These are an `Acquire` that returned `Ready(Ok)` and a successful `try_acquire`, and they are not yet `release`d
- total: `n` + permits added by `release` as new permits − permits removed by `forget_permits`

Statement (P1, conservation). The following holds in every reachable state of every execution. It holds for any number of threads and `Acquire` futures, with `poll`, `drop`, `release`, `close`, `try_acquire` and `forget_permits` interleaved in any order at atomic-operation granularity:

  available + Σ over queued futures of owed + Σ over running calls of local + held = total

Every call also returns with its local permits at 0. A call cannot leave permits in a local that dies with it.

Also proved
- a future that completed (`Ready(Ok)` handed its permits to the caller) or that was dropped is never in the wait list. This is the property the intrusive list needs to avoid dangling pointers. Memory safety itself is not proved
- every `assert!`/`assert_eq!` in the covered functions holds. That includes `prev + permits <= MAX_PERMITS` in `add_permits_locked`, so the "would overflow" panic cannot fire when new permits come only from the budget (below)
- drop of a future that is not queued touches nothing; drop of a queued future returns exactly its owed permits

Client obligations (preconditions; the theorem is about clients that meet them)
- a future is not polled after it returned `Ready(Ok)`. The `Future` contract leaves that unspecified
- `release(k)` takes a ghost token for `k` held permits, or `k` units of a budget for new permits. The budget is created by `new` as `MAX_PERMITS − n`. So callers never release permits they do not have, and never exceed `MAX_PERMITS`
- Rust runs `Acquire::drop` once when the future is dropped (see trusted assumptions)

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
  - Verus checks that the initial state satisfies them and that all 20 transitions preserve them
- each atomic's ghost invariant ties the real value to its token
  - the counter word: `v == 2·permits + closed`
  - each waiter: `state == ws.state`
  - so the ledger equation is about the real atomics, not copies of them
- each executable function's ghost code performs exactly one transition per real atomic step, inside that step's `atomic_with_ghost!`. One local per call is a map token keyed by the call. Its contract requires it to come back at 0. Verus tokens may be dropped silently, but a token cannot be re-minted for a key the ledger still has. So the only way to satisfy the contract is to move the permits somewhere the ledger counts
- why the close fix is needed: on the `waiters.closed` early return, `acquired` permits sit in the local. Without the fix, `poll_acquire`'s postcondition `fl.value() == 0` fails

## Checks that the proof is not vacuous

[semaphore_proof/mutate.py](semaphore_proof/mutate.py) verifies the original, then five variants, each with one known bug. Run 2026-11-20 under `cpu-run LOW`, Verus `840fa612c` (2025-11-30 build):

```
original: exit 0: verification results:: 88 verified, 0 errors
master_no_close_fix: exit 1: verification results:: 87 verified, 1 errors (rejected)
pre8542_fast_path: exit 1: verification results:: 87 verified, 1 errors (rejected)
drop_no_return: exit 1: verification results:: 87 verified, 1 errors (rejected)
drop_no_remove: exit 1: verification results:: 87 verified, 1 errors (rejected)
poll_clear_on_pending: exit 1: verification results:: 87 verified, 1 errors (rejected)
```

Each failure is for the expected reason:
- `master_no_close_fix` (real master `fc0d151`) and `pre8542_fast_path`: `poll_acquire` postcondition `fl.value() == 0`. The permits are still in the local when the call returns
- `drop_no_return`: `Acquire::drop` postcondition `self.fl@.value() == 0`
- `drop_no_remove`: the precondition of the `retire` transition. That transition requires the waiter to be off the list
- `poll_clear_on_pending`: `Acquire::poll` postcondition `self.wf()`. `queued` no longer matches the future's phase

The bounded checker ([TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md)) rejects the same four drop and fast-path mutations. It also finds the `close` leak on master.

## How the proof is tied to the real code

The Verus file is the real source with ghost code added and a listed set of changes, each marked `// VERUS:`.

[semaphore_proof/correspond.py](semaphore_proof/correspond.py) checks this mechanically, function by function:
- input: the nine covered functions of the real file (master + fix; comments and `tokio_unstable` tracing items removed)
- method: erase ghost syntax (`proof` blocks, tracked/ghost lets, `Tracked`/`Ghost` arguments), turn `atomic_with_ghost!(&x => op(args); ..)` back into `x.op(args)`, drop memory-ordering arguments
- check: each real statement line must appear in the Verus function in the same order
- result: 100 of 186 real lines are kept verbatim and in order

The 86 changed lines fall into these categories; the script prints each one:
- `MutexGuard` is explicit:
  - `waiters.closed` becomes `waiters.w.closed`
  - every lock acquisition also returns the ghost wait-list token
  - each implicit guard drop is an explicit `unlock`, including the drops on early returns. Rust drops guards implicitly; Verus has no verified `Drop` for guards
- `assert!`/`assert_eq!` become `runtime_assert(cond)`. It is trusted to panic exactly when `cond` is false; Verus proves `cond`
- control-flow sugar Verus does not accept, rewritten to its expansion:
  - `break value` from `loop`: kept in an `Option`
  - `let .. else`: written as a `match`
  - `r?`: written as a `match`
  - `ready!(..)`: expanded
  - `unwrap_or_else(|| ..)`: written as a `match`
  - `cmp::min`: a trusted `min`
  - an atomic call's result is bound to `res` before the `match`
- intrusive pointers
  - `Pin<&mut Waiter>`/`NonNull<Waiter>` become `Arc<Waiter>`
  - `queue.remove(NonNull::from(&mut self.node))` becomes `queue.remove(&self.node)`
  - `project()` is inlined as field accesses
- `waker.with_mut(|w| ..)` becomes the trusted `WakerCell::take`/`register`
- tracing and taskdump code (`trace_leaf`, `trace_poll_op!`, spans) is removed
- the `Pointers` field of `Waiter` is removed; the trusted list replaces it

Not mechanically checked: that the trusted stand-ins behave as specified, and that no real line was moved into a different branch. The in-order check does not detect a line moved to another branch; the mutation results and a manual read are the evidence for that.

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
- the other `Semaphore` entry points (`acquire_many`, `Semaphore::add_permits` wrappers in `semaphore.rs`, `SemaphorePermit`'s `Drop`), `Mutex`, `RwLock` and `mpsc` on top. Their correct use of `release` is a client obligation here
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
  - we do not claim the first verified cancellable semaphore; the claim is the first proof about Tokio's
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
7. Liveness (waiters are eventually woken), in the style of Lion or Li et al.

## Must not claim

- "verified Tokio's semaphore" without qualification. Say "a Verus proof of permit conservation for a minimally changed copy of Tokio's `batch_semaphore.rs` (master `fc0d151` + close fix), assuming sequential consistency and a trusted list spec"
- anything about master as shipped, beyond this: the proof fails there, consistent with the leak reproduced in loom
- liveness, unwind safety, or memory safety

## Reproduce

From `verification/async_cancel/semaphore_proof/`, with `VERUS` the Verus binary (built from `verus-lang/verus` `840fa612c`):
- `$VERUS --crate-type=lib batch_semaphore.rs` → `verification results:: 88 verified, 0 errors` (about 5 s)
- `python3 -I mutate.py $VERUS` → the six lines above; exit 0
- correspondence:
  - clone Tokio into a scratch dir
  - `git checkout fc0d151753b5fb10125ecef2d48f29b192c9abcf && git apply .../real_tokio/semaphore-close-fix.patch`
  - `python3 -I correspond.py SCRATCH/tokio/src/sync/batch_semaphore.rs` → per-function counts, `total changed lines: 86`

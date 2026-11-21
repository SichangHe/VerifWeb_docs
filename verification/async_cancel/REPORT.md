# Verus async support and cancellation: study
(authored by agents unless marked 🧑)

As of 2026-11-13, Verus supports some real `async fn` bodies and `.await`, but a proof of their completion postconditions does not prove cancellation safety. Our executable counterexample verifies, suspends, and is dropped with the intermediate state still visible. Extending cancellation verification is a smaller and more specific problem than implementing async from scratch.

Follow-up: the human authorized proceeding with our choice of approach. We reproduced the real Pingora failure and the proposed repair, then checked its compiler-generated cancellation path. See [the real-library regression](real_pingora/README.md) and [the MIR check and remaining obligations](MIR_CHECK.md). The [cleanup translator](CLEANUP_SEMANTICS.md) derives map-effect obligations from the real destructor's instructions; Verus proves both paths equal the [cleanup specification](cleanup_contract.rs). The [publication interpreter](PUBLICATION_MIR.md) enumerates cache/map hit-or-miss outcomes and checks matching guard construction and preservation across repeated Pending polls for cases reaching direct lock registration. These rely on trusted interpreters, compiler output and stated dependency contracts. Whole-function coverage, initial capture-schema assumptions and panic behavior remain outside the result; a complete library proof remains open. Follow-up 2026-11-18: [panic/unwind paths](UNWIND.md) of the same compiled code are now checked; the fix keeps the invariant on unwind except at four library-call unwind edges before the guard exists and inside the guard destructor, while the buggy parent fails on user-callback panics. Follow-up 2026-11-18: the same method applied to Tokio's `Notify` ([TOKIO.md](TOKIO.md), fix tokio-rs/tokio#3652): MIR facts from the real `Notified` destructor let Verus prove, in a transition system whose drop step is extracted from MIR and whose other operations are hand-modelled, that cancelling a waiter never loses a `notify_one` permit at the fix, and reject the buggy parent; Tokio's regression fails on the parent and passes on the fix.

## Claims and prior work

🧑 Human, 2026-11-18, verbatim: "So it seems like we need to be more careful when we claim that we formally verify type V. We need to look at what prior work has done, and so on. Relay this and note this down to the relevant agents, and persistent docs."

Rule for this study: before any "we verify X" claim, name the prior checking of X and state exactly what is new: model vs real code, safety vs liveness, and what is trusted. None of our results is a refinement proof of real compiled code. The earlier results are Verus proofs over a transition system whose facts are extracted from real compiled MIR by a trusted Python interpreter. The Tokio batch-semaphore proof (below) instead verifies a hand-adapted Verus copy of the real source: 116 of 215 real lines of the covered functions kept verbatim, the rest rewritten in listed categories, including `Pin`/`NonNull` and the intrusive list replaced by `Arc` plus a trusted-spec list, and `Drop` made a plain method. Prior-work search done 2026-11-18; not exhaustive.

Prior work on async runtimes generally
- Lion (Zhou, Zhang, Chowdhury, Mu, [SOSP '26](https://doi.org/10.1145/3830418.3843879)), abstract: "We demonstrate this framework via Lion, a Tokio-compatible runtime in Rust verified using Verus." It is a new runtime, not Tokio's code. Its user-code assumptions include that a task "does not cancel another task's pending wait". Its `Notify` cancellation glue is trusted; see [LION.md](LION.md).
- Li, Beschastnikh, Summers, [arXiv:2610.09198](https://arxiv.org/abs/2610.09198), abstract: "use these to verify eventual progression of several key components of multiple Rust async runtime implementations". The evaluated Tokio components are oneshot receivers (`OneShot-recv`, `OneShot-closed`). Section 7 names as gaps "a wake-one primitive ... for single-permit synchronization idioms (e.g., tokio's Mutex, Semaphore)", and: "Our model currently has no notion of obligation revocation and no mechanism for a reactor to learn that a transferred obligation becomes irrelevant".
- Neither verifies cancellation safety of application or library code built on a runtime. That is a statement about these two papers, not about all literature.

Tokio `Notify` #3652 ([TOKIO.md](TOKIO.md))
- prior: Tokio runs [loom](https://github.com/tokio-rs/loom) model checking over the real `Notify` source, with loom's atomics substituted. It explores interleavings of fixed small test programs, so it is bounded. At the fix commit `f7c181c`, `tokio/src/sync/tests/loom_notify.rs` has `notify_one`, `notify_waiters`, `notify_multi` and `notify_drop`. `notify_drop` drops a polled `Notified` but never calls `notify_waiters`, which the PR's bug trace requires. At current master `fc0d151`, `notify_waiters_and_one` mixes the two calls but drops no pending future. Inference from reading the tests (we did not run them): no loom test covers the #3652 trace. The fix's own integration test does.
- prior: Lion verifies a different `Notify` (its own); Li et al. do not model wake-one primitives.
- ours adds: safety (no permit lost on drop) for all interleavings and unbounded traces, at the 2021 commits only. The drop step is extracted from real MIR; the buggy parent is rejected.
- must not claim: "verified Tokio's Notify" or "verified current Tokio". `notify_one`, `notify_waiters` and `poll` are hand-modelled. Liveness and unwind are not covered. Atomicity is argued, not checked, where loom checks it for small programs.

Tokio `Notify` at current master `fc0d151` ([TOKIO_CURRENT.md](TOKIO_CURRENT.md))
- prior: the same loom suite. Observed: with the #3652 guard removed from current `drop_notified`, all 9 existing loom Notify tests still pass.
- ours adds: the real MIR of all five operations (`notify_one`/`notify_last`, `notify_locked`, `notify_waiters`, `poll`, drop) is executed by an abstract interpreter. It searches every number of futures and threads exhaustively under stated C11 stale-load rules. Result: no non-receive step loses a pending permit. Four MIR mutations are rejected. Three new loom tests pass on master; one fails on the re-injected #3652 bug.
- must not claim: a Verus or refinement proof, or "verified Tokio's Notify". The result is a search over a sound finite abstraction by a trusted Python interpreter, for one safety property on normal paths. Library semantics, some counter facts and the C11-to-interleaving argument are trusted.

Tokio batch semaphore at current master `fc0d151` ([TOKIO_SEMAPHORE.md](TOKIO_SEMAPHORE.md))
- prior: Tokio's 8 loom semaphore tests over the real code (fixed small programs; no coop budget under loom); integration tests including `mutex_coop_drop_after_take_permit` (#8371) and the #8542 tracing-panic test; `tokio/fuzz` has only `fuzz_linked_list`. CQS ([arXiv:2111.12682](https://arxiv.org/abs/2111.12682)) formally verifies a different cancellable semaphore, for Kotlin. Li et al. list Tokio's Semaphore as a gap
- ours adds: a bounded exhaustive check of permit conservation, interpreting the real master MIR of all ten semaphore operations. Futures may be polled or dropped at any point, coop `Pending` is allowed at any poll, and stale waiter-state loads are allowed. Result: drop never loses permits when the semaphore is not closed; 4 MIR mutations are rejected, including #8542's parent with master's coop order
- counterexample: a permit leak when `close` races a re-poll of a queued waiter. It appears under SC too and is reproduced by a running loom test on master (`permit leaked`). No upstream report was found. A second loom test shows the effect: bounded `mpsc` `recv` after `rx.close()` never returns `None` while a sender lives; a candidate one-line fix makes both tests pass. Drafts for upstream: [UPSTREAM_DRAFTS.md](UPSTREAM_DRAFTS.md). Nothing was filed
- must not claim: "verified Tokio's semaphore". The check is bounded (≤3 futures, ≤4 permits), covers normal paths only, uses a trusted Python interpreter, and is not a Verus or refinement proof

Tokio batch semaphore, unbounded proof, master `fc0d151` + candidate close fix ([SEMAPHORE_PROOF.md](SEMAPHORE_PROOF.md))
- prior: everything listed for the bounded check above. CQS is the closest verified cancellable semaphore (Kotlin, a different algorithm). Lion verifies its own waiter kernel (`remove_step`) and trusts its cancellation glue
- prior, Joshi et al., "Validating a High-Performance Cloud Object Store with Lightweight Formal Methods", SOSP '26 ([doi:10.1145/3830418.3843899](https://doi.org/10.1145/3830418.3843899)), p. 700: "We also extended our test framework to inject task drops at intermediate await points (to check cancellation safety)". Also p. 700: "we reimplemented Tokio's concurrency primitives so they can be controlled by the Shuttle runtime". This is testing of application code (S3 Express) under sampled schedules, against stand-ins for Tokio's primitives. It is not a proof, and not about Tokio's semaphore
- ours adds: Verus `88 verified, 0 errors` for a hand-adapted Verus copy of `batch_semaphore.rs`: 116 of 215 real lines of the 12 covered functions kept verbatim and in order; the rest rewritten in listed categories (including `Pin`/`NonNull` plus the intrusive list replaced by `Arc` plus a trusted-spec list, and `Drop` made a plain method); every added line is marked `// VERUS:` or in an allowed category (checked by `correspond.py`). Theorem: in every reachable state, available + permits owed to queued futures + permits in running calls' locals + permits held by callers = initial + added − forgotten, and every call returns with no local permits. It holds for any number of futures, permits and threads, under cancellation at any poll and `close`. The copy without the fix block and four other bad variants each fail verification at the expected clause. Caveat: `held` is a ghost token, so the theorem covers only clients that meet the ghost obligations; overflow freedom relies on the client staying within the ghost budget
- trusted: sequential consistency of atomics (the real code uses Acquire/Release); the intrusive-list spec (nodes as `Arc` with ghost ids); wakers and coop; that Rust runs `Acquire::drop` once; Verus/VerusSync. Clients must not poll after `Ready(Ok)` and must release only held or budgeted permits
- must not claim: "verified Tokio's semaphore" unqualified; anything about the shipped master except that the proof fails there; liveness, unwind or memory safety; a MIR-level or C11-level result. Open obligations are listed in SEMAPHORE_PROOF.md

Hyper HTTP/2 cancellation hand-off ([HYPER.md](HYPER.md))
- prior: h2 has in-tree cargo-fuzz targets (`fuzz_client`, `fuzz_e2e`, `fuzz_hpack`). The OSS-Fuzz harness repo [hyperium-fuzz](https://github.com/hyperium/hyperium-fuzz), "Consolidated fuzzing for hyperium crates", targets `h2`, `http`, `httparse` and `httpdate`; its last commit is 2023-07-06. We found no fuzz target for Hyper's client dispatch (`SendWhen`, `PipeMap`), and no model checking or verification of Hyper or h2.
- prior: Lion's utility-to-runtime chain assumes the peer signal that Hyper's fix adds; see [LION.md](LION.md).
- ours adds: a safety hand-off property over unbounded interleavings, with facts extracted from real MIR at `5b17a69`; the parent is rejected. [UNWIND.md](UNWIND.md) adds an unwind gap confirmed at runtime.
- must not claim: that RST_STREAM is eventually sent (liveness), or anything about h2 internals, which are trusted. The transition system is reviewed by hand, and channel exclusivity rests on a source search.

Hyper HTTP/2 hand-off at current master `21da6a59` ([MASTER.md](MASTER.md))
- prior: as above; plus our `5b17a69` check, whose checker hard-coded field indices that master's new `is_head` fields shifted
- ours adds: the same facts and Verus proof (`9 verified, 0 errors`) on master MIR, with field indices now derived from the compiled projection literals; Hyper's #4040 regression passes. The tracing-unwind gap still exists on master, confirmed by a running test.
- must not claim: "verified current Hyper". Same trust and limits as `5b17a69`: normal paths only, no liveness, hand-reviewed abstraction, trusted extraction.

Pingora cache lock ([CONDITIONAL_CHECK.md](CONDITIONAL_CHECK.md), [UNWIND.md](UNWIND.md))
- prior: we found no published verification, model checking or fuzzing of `pingora-memory-cache`. A web search for Pingora with formal verification or model checking found only bug-bounty fixes ([Cloudflare blog](https://blog.cloudflare.com/pingora-oss-smuggling-vulnerabilities/)). The pinned `read_through.rs` has one unit-test module.
- ours adds: cancellation and unwind safety of the lock invariant for the real compiled `RTCache::get`, conditional on stated library contracts and no-unwind assumptions; the parent is rejected.
- must not claim: an unconditional or complete library proof, liveness, or that we are first to verify async cancellation in Verus. Lion verifies a cancellation step (`remove_step`).

Pingora cache lock at current master `3f87e92` ([MASTER.md](MASTER.md))
- prior: PR #1037 itself describes the bug; it is still open, unmerged
- ours adds: a running test shows the cancellation leak on master (`RTCache::get() is stuck`); master's `read_through.rs` is identical to the buggy parent, and our checkers reject it as they reject the parent
- must not claim: any positive result for shipped Pingora. Our positive results cover only the unmerged PR head `b2aeef4`.

## Evidence and version boundary

The [ownership proof generator](OWNERSHIP_OBLIGATIONS.md) gives Verus the interpreted guard values and abstract resume equations; Verus proves initial ownership and preservation across arbitrarily many Pending polls. The [destruction proof generator](DROP_OBLIGATIONS.md) supplies the actual cancellation edges and a candidate invariant; Verus proves that every finite path ending in a normal return has successfully dropped the guard. These strengthen the previous Python safety checks; interpretation and MIR translation remain trusted components.

The [combined conditional check](CONDITIONAL_CHECK.md) runs structural coverage, ownership, cancellation-path and cleanup verification against paired compiler artifacts. Interpretation starts at the initial coroutine dispatch and derives the saved arguments and hashed key for all eight cache/map lookup-outcome schedules, conditional on normal-returning calls and repeated Pending polls. Captures and saved guard positions are cross-checked against compiler metadata. Cases stopped before publication cannot reach the sole direct insertion. Structural checks also exclude further suspension after callback Ready; they do not by themselves prove semantic coverage of every branch. Two [independently compiled Rust mutations](real_pingora/SOURCE_MUTATIONS.md) are rejected; matching artifacts from one build remains an explicit assumption.

We tested the latest available rolling binary, `0.2026.11.05.31e44e6`, then built and tested main at `6ae5f7b97c6403789fc1f12117ea8b2f0092289c` (`0.2026.11.13.6ae5f7b`) with its matching standard library. The latest stable release, `0.2026.11.02.8bf68ee`, predates the async soundness repair merged November 4. The rolling binary predates the cross-module repair merged November 13. Results on these versions must not be conflated. [UPSTREAM.md](UPSTREAM.md) records issue status, contributors, and source quotations; [TESTS.md](TESTS.md) records the support probes.

The rolling-release probes verify async return postconditions, a mutable borrow spanning an await, and a simple handwritten `Future::poll` with its result specification. False completion postconditions fail. Inline async blocks produce “Verus does not currently support coroutine types”; async trait declarations produce “Verus does not currently support `impl Trait` types in trait definitions”. The exact cross-module future-creation case in #3439 fails, while a cross-module awaiting caller works. The #2541 compiler crash does not reproduce, but that example verifies zero functions and therefore does not demonstrate verified async trait support.

The same suite passes its expected outcomes on November 13 main, with the #3439 case changed to successful verification. The compiled cancellation experiment still leaves state `1`. Thus today's cross-module fix is confirmed by execution; it does not change the cancellation conclusion.

A minimal Cargo project using the same source revision's `vstd` also reports “verification results:: 2 verified, 0 errors”. The generic claim that Cargo cannot verify any async function does not hold for this matched current build. This does not establish support for arbitrary dependency graphs or reproduce the original reporter's full environment.

The locally supplied solver works with the rolling release; its bundled Z3 failed with `version 'GLIBC_2.38' not found`. Setting `VERUS_Z3_PATH` to the compatible local Z3 resolves that environment failure. The launcher still prints a weak `GLIBC_2.39` warning, but verification and compilation succeed.

To rerun all probes and the compiled cancellation experiment, set `VERUS` and, if needed, `VERUS_Z3_PATH`, then run `bash verification/async_cancel/run.sh`. For main after #3440, also set `EXPECT_CROSS_MODULE_CREATE_EXIT=0`; the default expects the rolling release's known failure. The runner uses one verifier thread, bounds each invocation with a timeout, prints failures, and deletes temporary logs and binaries.

## What the cancellation experiment establishes

[cancel_runtime.rs](cancel_runtime.rs) verifies the actual async function that is compiled and executed. It writes `1` through a mutable reference, awaits a supplied future, then writes `2`. Its postcondition is `ensures *final(state) == 2`. The unverified runtime harness supplies `std::future::pending()`, polls once, and drops the enclosing future.

Observed verifier output: `verification results:: 1 verified, 0 errors`. Observed program output: `state after cancellation: 1`. There is no `assume`, `admit`, or `external_body` in this file. The runtime harness is a test, not a verified client.

Inference: completion verification alone does not establish the desired property, namely that cancelling this operation restores the externally accessible state. This example is not by itself a soundness violation: a completion postcondition need not hold when an operation never completes. It is also not a library proof or a claim that all mutable-reference async specifications are sound.

## Why this gap exists

Main's [await translation](https://github.com/verus-lang/verus/blob/6ae5f7b97c6403789fc1f12117ea8b2f0092289c/source/vir/src/ast_to_sst.rs#L3835-L3861) replaces `ExprX::Await(e)` with a call to `future::exec_await`. That function's [contract](https://github.com/verus-lang/verus/blob/6ae5f7b97c6403789fc1f12117ea8b2f0092289c/source/vstd/future.rs#L65-L82) says:

```rust
ensures
    future.awaited() == true,
    future.obeys_future_laws() ==> ret == future@,
opens_invariants any
```

These are completion facts. There is no cancellation branch in this translation or a drop postcondition in this contract. The future trait's `poll` specification constrains `Ready` results and preserves the predicted result across `Pending`, conditional on `obeys_future_laws()`. It does not describe application cleanup when the future is destroyed.

This abstraction makes ordinary functional reasoning possible without verifying the generated coroutine state machine. It loses exactly the suspended states and cleanup transitions needed here. This is an inference from the implementation, not a statement of the maintainers' reasons for prioritizing features. Upstream is actively repairing async support and preparing async trait support; the survey found no published commitment to implementing cancellation contracts.

Existing invariant restrictions help: `exec_await` may open any invariant, so a caller cannot generally await while holding one open. That prevents a particular misuse of Verus invariants. It does not express a cache-specific requirement that every published lookup has an owner that will complete or clean it up.

Drop is a separate complication. The [guide](https://github.com/verus-lang/verus/blob/6ae5f7b97c6403789fc1f12117ea8b2f0092289c/source/docs/guide/src/reference-unwind-sig.md#L45-L47) says, “If you implement `Drop` for a type, you are required to give it a signature of `no_unwind`.” Open issue [#3209](https://github.com/verus-lang/verus/issues/3209) reports implicit generic drops that can unwind or reenter invariants, including the drop of an unpolled future. A cancellation proof must account for destructor effects; passing the existing completion checks is insufficient.

Our destructor probes also establish that Verus accepts cleanup through an exclusive reference but requires `opens_invariants none`: omitting it produces “a `Drop` implementation must be marked `opens_invariants none`”. The [well-formedness check](https://github.com/verus-lang/verus/blob/6ae5f7b97c6403789fc1f12117ea8b2f0092289c/source/vir/src/well_formed.rs#L1737-L1758) also forbids explicit `requires`. Thus the usual proof of lock-protected shared cleanup by opening a Verus invariant cannot simply be placed inside today's verified destructor. This matters directly to the Pingora guard and remains work even with an explicit future.

## Real-code targets

### Pingora cache lookup

Reporter YZL0v3ZZ's [issue #931](https://github.com/cloudflare/pingora/issues/931) states: “`pingora-memory-cache::RTCache::get()` can leak a per-key lookup-coalescing lock if the cache-miss writer future is cancelled while it is awaiting the user-provided `Lookup::lookup()` callback.” It remains open. We inspected the [pinned source](https://github.com/cloudflare/pingora/blob/e6e677fe9b58555140ab7bd14feff035392b3530/pingora-memory-cache/src/read_through.rs#L150-L282): `lockers.insert(hashed_key, new_lock2)` precedes `let value = CB::lookup(key, extra).await`; `my_write.lock.add_permits(10)` and `lockers.remove(&hashed_key)` follow it. We subsequently executed the buggy and repaired versions; see [the reproduction](real_pingora/README.md).

The failure is a good first target because its safety condition can be stated locally: after dropping a writer, its lookup marker cannot remain as an unreleasable zero-permit lock. Existing readers holding an `Arc` also need notification, so deleting the map entry alone is insufficient. Cleanup must identify the lock instance it owns, so an old writer cannot remove a replacement writer's entry.

Contributor kevhoward20011-oss's open [PR #1037](https://github.com/cloudflare/pingora/pull/1037) says: “This change makes lock ownership cancellation-safe by tying cleanup to a guard whose Drop implementation releases only the specific lock instance it owns.” Its reported “Verification” is reproduction and regression testing, not evidence of a formal proof. The patch offers a concrete buggy/fixed pair for a later proof experiment.

Full proof dependencies: actual map operations and locking; `Arc` identity; semaphore release/wakeup behavior; the callback future's pending and drop behavior; and the guard's actual destructor. Treating any of these as an external specification must be explicit. Proving notification was issued is a safety property; proving a waiting task eventually progresses additionally requires scheduler and callback progress assumptions.

### Hyper HTTP/2 request cancellation

This target has stronger upstream confirmation. The merged [fix #4042](https://github.com/hyperium/hyper/commit/5b17a69ebcf969471c1a19b25ed2cb81299d1be6) states: “When the client drops the response future (e.g. due to a timeout), send_task detects the cancellation but does not notify pipe_task.” The patch adds a oneshot cancellation channel and calls `send_reset(CANCEL)` from `PipeMap::poll`; it closes [#4040](https://github.com/hyperium/hyper/issues/4040).

This is already expressed partly as manually implemented `Future::poll`. It is a useful second target for reasoning about cancellation propagation between tasks. A per-await exit check alone cannot prove the receiver runs or the remote peer receives a reset. Start with the safety obligation that a detected cancellation either transfers a reset obligation to a live task or resets the stream directly. Separate eventual reset delivery from that theorem. Follow-up: [Hyper hand-off check](HYPER.md) proves this safety obligation for the fixed commit's compiled MIR and rejects its parent, conditional on listed trusted contracts; Hyper's regression test fails on the parent and passes on the fix. Eventual delivery remains unproved. Its [unwind coverage](UNWIND.md) shows the hand-off is lost if send_task unwinds between detection and `Sender::send`.

## Workarounds and extensions

These are proposed scopes, not implemented proofs or effort estimates.

### A. Extend Verus at suspension boundaries

Retain the actual async Rust body. Add an application cancellation contract and verification obligations for destruction of every reachable suspended state. A minimal first version could require the shared-state invariant to survive cancellation without cleanup, reject unsupported destructors and futures, and handle one concrete await at a time. That would detect the Pingora pattern but would not accept its guard-based repair.

To accept that repair, each obligation must execute or soundly summarize destruction of the child future and all live fields in Rust's actual order, then establish the application invariant. Checking an invariant immediately before the textual `.await` is insufficient: polling the child can modify shared state before returning `Pending`, and its destructor can modify state again. Cover creation followed by drop before the first poll, nested awaits, every `Pending` return, and destruction after completion. Panic paths need an explicit scope or proof; “no panic” cannot be silently assumed for unknown generic destructors.

Implementation boundary: use compiler-derived coroutine layouts and drop information, or a restricted source translation whose correspondence to that information is checked. Ordinary completion contracts for third-party futures are insufficient; need summaries for pending polls and cancellation effects. Existing Verus ownership and invariant machinery can discharge local obligations, but the translation and its soundness argument are new work.

### B. Explicit executable state machine with a drop step

Encode states, `poll`, and cleanup explicitly and prove each transition preserves the invariant. This is suitable for an early diagnostic model and fits Hyper's existing manual futures. A proof of a hand-written model alone does not meet the human's requirement to prove the real code conforms to the specification.

To meet that requirement, either verify the actual production state-machine implementation, or establish a checked correspondence between the compiler's async state machine and the verified one. Replacing a production `async fn` with a verified manual future also requires demonstrating the intended externally visible behavior, including pinning, borrows, drop order, and cancellation. Calling a verified cleanup helper from an unverified destructor still leaves the connection unproved. Existing drop support must be tested or extended rather than assuming a modeled `drop` action represents Rust's implicit destructor execution.

### C. Verify compiler-generated states with another backend

A verifier working on Rust's lowered intermediate representation could inspect the real coroutine and its drop code. This avoids hand translation but still needs suitable models of shared memory, external APIs, and scheduling. Bounded checks of a real cancellation harness are valuable evidence and regression tests; bounds prevent claiming an unrestricted theorem. A new backend or a sound translation to Verus is research work, not an available turnkey workaround established by this study.

### D. Make operation ownership survive caller cancellation

An application can hand the operation to an owning task and let cancellation discard only the response receiver. This may simplify the shared-state invariant, but it changes semantics and does not prove the original implementation safe. It moves the obligation to worker shutdown, failure, and cancellation. It does not cover Hyper's failure automatically: a surviving body task is precisely part of that bug.

## Recommended next experiment and decision

Recommendation: first verify a narrow Pingora-style writer-ownership invariant against the real buggy and fixed implementation paths, with an explicit list of trusted dependency specifications. Require the buggy version to fail the cancellation obligation and the guard-based repair to pass. The deliverable must identify how actual Rust destruction is connected to the proof; otherwise label it a model experiment.

The human subsequently authorized choosing the approach. We chose compiler-derived checking first, preserving the production async body while examining its actual destruction paths. This study does not establish that either source rewriting or compiler-derived checking already supports a complete cancellation proof.

For openraft and Automerge networking, ordinary async control flow is no longer a blanket reason to stop. The probes and upstream limitations identify what can be attempted now. Cancellation, concurrent state changes, unsupported traits/APIs, and the connection to compiled code remain independent obligations. The existing [openraft report](../raft_membership/REPORT.md) explicitly describes a “hand transliteration”; these findings do not close that gap.

## Literature boundary

The later [Lion artifact assessment](LION.md) establishes that Lion includes verified cancellation steps, while its real-future cleanup glue remains trusted and some task-abort traces remain outside its theorem. Its utility-to-runtime chain assumes that a peer signals; checking Hyper's application cancellation-to-notification code remains a distinct proposed target. This is an artifact-based comparison, not a complete literature survey.

A Google Scholar query for `Rust async cancellation formal verification` through `pb-browser-page-extract` encountered a CAPTCHA (`challenge_action_required`). We stopped without bypassing it. This study establishes tool behavior and upstream development status, not literature completeness or research novelty. No papers were downloaded or added to the collection.

## Scholar update, 2026-11-14 (changed in this pass)

Five Scholar queries (2022 onward), snippets only. No paper found that verifies cancellation safety of async Rust (state consistent when a future is dropped at an await point). Closest:
- Gray, Krishnamurthi, Crichton, "A Design Space Exploration of Async/Await" (PACMPL 2026): a formal semantics and design survey; the only hit for the exact phrase "cancel safety". Snippet: "Smol implements task destruction using Rust's Drop trait, which only permi…". Semantics, not verification of programs.
- Sethi, Pan, Lu, Musuvathi, Nath, "Cancellation in systems: An empirical study of task cancellation patterns and failures" (OSDI 2022): bug study, not Rust async, no proofs. Good motivation citation.
- Lion (Zhou, Zhang, Chowdhury, Mu, SOSP 2026) and Li, Beschastnikh, Summers (arXiv 2610.09198, 2026) verify liveness of async runtimes (tasks are eventually woken); Lion also verifies a waiter-cancellation kernel step, with trusted Drop glue (correction: see LION.md). They are the closest Verus-on-async work and must be cited; Lion shows Verus can reason about a Tokio-compatible runtime.
- Drodt, "A Complete, Formal Semantics for Rust Source Code" (arXiv 2610.06003, 2026) mentions async composition rules; not checked whether it models drop of suspended futures.

Verdict: partly covered by Lion at the runtime level; application-level cancellation safety still open.

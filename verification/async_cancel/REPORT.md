# Verus async support and cancellation: study
(authored by agents unless marked 🧑)

As of 2026-11-13, Verus supports some real `async fn` bodies and `.await`, but a proof of their completion postconditions does not prove cancellation safety. Our executable counterexample verifies, suspends, and is dropped with the intermediate state still visible. Extending cancellation verification is a smaller and more specific problem than implementing async from scratch.

Follow-up: the human authorized proceeding with our choice of approach. We reproduced the real Pingora failure and the proposed repair, then checked its compiler-generated cancellation path. See [the real-library regression](real_pingora/README.md) and [the MIR check and remaining obligations](MIR_CHECK.md). The [cleanup translator](CLEANUP_SEMANTICS.md) derives map-effect obligations from the real destructor's instructions; Verus proves both paths equal the [cleanup specification](cleanup_contract.rs). The [publication interpreter](PUBLICATION_MIR.md) checks matching guard construction and preservation across repeated Pending polls for the conditional map-miss path. These rely on trusted interpreters, compiler output and stated dependency contracts. All-entry coverage, initial frame assumptions and panic behavior remain outside the result; a complete library proof remains open.

## Evidence and version boundary

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

This is already expressed partly as manually implemented `Future::poll`. It is a useful second target for reasoning about cancellation propagation between tasks. A per-await exit check alone cannot prove the receiver runs or the remote peer receives a reset. Start with the safety obligation that a detected cancellation either transfers a reset obligation to a live task or resets the stream directly. Separate eventual reset delivery from that theorem. We inspected the fix, but have not verified Hyper or run its regression test.

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

A Google Scholar query for `Rust async cancellation formal verification` through `pb-browser-page-extract` encountered a CAPTCHA (`challenge_action_required`). We stopped without bypassing it. This study establishes tool behavior and upstream development status, not literature completeness or research novelty. No papers were downloaded or added to the collection.

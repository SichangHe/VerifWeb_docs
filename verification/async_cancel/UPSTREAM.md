# Verus async upstream survey
(authored by agents unless marked 🧑)

Surveyed 2026-11-13 using GitHub's issue, pull-request, review, and comment APIs. Statuses below are the observed GitHub states, not independent reproduction results. The accompanying test report determines which reported limitations reproduce in the tested build. No maintainers were contacted.

## What the upstream work establishes

Basic `async fn` verification is implemented. FeizaiYiHao's [#1993, “support async functions”](https://github.com/verus-lang/verus/pull/1993), merged April 10, 2026, checks the body and exposes its result conditionally on completion. The final design discussion says: “For async function body checks, since the above approach, we can perform the checks almost 100% the same as normal functions.” It then describes rewriting `ensures ret > 0` into `VERUS_INTERNAL_ASYNC_ret.awaited() ==> {let ret = VERUS_INTERNAL_ASYNC_ret@; ret > 0}` ([FeizaiYiHao](https://github.com/verus-lang/verus/pull/1993#issuecomment-3667439463)). The opening PR description predates that design revision and must not be read as the final user syntax.

This is completion reasoning, not a cancellation contract. In the inspected [future specification](https://github.com/verus-lang/verus/blob/6ae5f7b97c6403789fc1f12117ea8b2f0092289c/source/vstd/future.rs#L68-L80), the await abstraction is:

```rust
#[verifier::external_body]
fn exec_await<F: Future>(
    #[allow(unused_variables)]
    future: F,
) -> (ret: F::Output)
    ensures
        future.awaited() == true,
        future.obeys_future_laws() ==> ret == future@,
    opens_invariants any
{
    unimplemented!()
}
```

Inference from this contract: it describes a returned result and constrains which Verus invariants may already be open; it does not specify the observable state when the future is dropped before returning. It cannot by itself justify cancel-safety of a library operation. Requiring `opens_invariants any` prevents awaiting while a conflicting invariant remains open, but does not supply a general rollback or drop proof for application state.

The proposed guide is still an **open PR**, [#2322](https://github.com/verus-lang/verus/pull/2322), authored by dschoepe. Its [draft text](https://github.com/verus-lang/verus/pull/2322/files) says: “The mutations are only known to have taken effect once the future has been awaited.” It explains: “Verus treats this imprecisely and considers `x` to have an unknown value as soon as it is passed to `mutating_arg`, until the resulting future is `await`ed.” For its `tokio::select!` wrapper, it says: “The above postcondition is *trusted*! Verus does not check that the body in fact guarantees the postcondition.” That approach falls short of the human's requirement to prove the real code conforms to the spec. The draft also predates the November future-law change, so its examples are not current support tests.

## Required issues and PRs

- [#1993](https://github.com/verus-lang/verus/pull/1993), **merged 2026-04-10**, FeizaiYiHao: initial verified async functions. See the completion semantics above; merging this feature does not establish full Rust async coverage.
- [#3234](https://github.com/verus-lang/verus/pull/3234), **merged 2026-11-04**, FeizaiYiHao: repairs an overstrong await specification and adds minimal `Pin` support. Author: “Only `await` called on `impl Future` variables with `obeys_future_laws() == true` will have the return value set to be equal to its `.view()` value.” Also: “`awaited` now is implemented by vstd for all types as an uninterp spec fn. Previous it could be implemented by users and lead to soundness issues.” This is result-law repair, not cancellation modeling.
- [#3440](https://github.com/verus-lang/verus/pull/3440), **merged 2026-11-13**, FeizaiYiHao: “Fixed the prune logic for async function cross module.” Fixes [#3439](https://github.com/verus-lang/verus/issues/3439), now closed. The issue explains: “The pruning logic keeps these functions, and `future::exec_await`, only when a root function in the module being verified is async.” Reached async functions from another module or crate needed the same retention rule.
- [#2322](https://github.com/verus-lang/verus/pull/2322), **open**, dschoepe: guide chapter, not an implementation PR. Its trusted-library wrapper limitation is quoted above.
- [#2595](https://github.com/verus-lang/verus/issues/2595), **open**, amaurremi: “Verifying any `async fn` via `cargo verus` results in a panic, but the same code using `verus <file>` verifies.” This is an unresolved report, not established evidence that all current Cargo verification fails. [tjhance](https://github.com/verus-lang/verus/issues/2595#issuecomment-4802930344): “I wasn't able to reproduce these. I'm not sure of the exact mechanism, but I suspect some kind of verus/vstd version mismatch. Is that a possibility?” [mkovaxx](https://github.com/verus-lang/verus/issues/2595#issuecomment-5020269061) requests pinning `vstd` to the exact Verus commit.
- [#3027](https://github.com/verus-lang/verus/issues/3027), **open**, tjhance: an `#[verifier::atomic] async fn` containing `await` passes. Author: “This is not technically a soundness bug, because the invariant masks still prevent you from calling await while an AtomicInvariant is open.” This concerns enforcement of the atomic annotation, not evidence that open atomic invariants may span `await`.
- [#3299](https://github.com/verus-lang/verus/issues/3299), **open**, tjhance; FeizaiYiHao working on it: tracked types held across suspension can disappear from the compiled opaque future's cross-crate type information and incorrectly permit `Send`. Author: “This can impact marker traits.” The precise design problem and current proposal appear below.
- [#2541](https://github.com/verus-lang/verus/issues/2541), **open**, amaurremi: an internal error with `--no-lifetime`, a generic trait, and a method returning `impl Future + Send` implemented by `async fn`. Author: “Without `--no-lifetime` the code verifies”. [tjhance's diagnosis](https://github.com/verus-lang/verus/issues/2541#issuecomment-4690217860): “in the --no-lifetime case, because we override the mir_borrowck, the "hidden types" is just the empty map that we return in the override”. The resulting fallback loses lifetime information. [#2549](https://github.com/verus-lang/verus/pull/2549), merged June 12 by tjhance, says “partially addresses #2541”; open status must not be interpreted as an unrepaired original reproducer.
- [#3209](https://github.com/verus-lang/verus/issues/3209), **open**, remi-delmas-3000: implicit destruction of generic values can unwind or reenter an invariant without a corresponding verification check. The report includes an **unpolled future** capturing a generic value: “the check has to cover every value whose drop glue can reach a type parameter, including opaque future types.” [tjhance](https://github.com/verus-lang/verus/issues/3209#issuecomment-6194405385): “This is, technically, documented behavior, but I agree it should be fixed.” The reported runtime counterexamples are upstream evidence; they have not been independently reproduced by this survey. This gap directly matters to proofs that depend on cleanup, even before an await occurs.

## Related repairs and unresolved work

[#3175](https://github.com/verus-lang/verus/issues/3175), reported by remi-delmas-3000, is **closed**. Its two distinct problems were: “Two futures that are equal in spec therefore await to equal results, although a `poll` with state returns different ones” and “the `into_future()` call that the binary runs is not verified.” The first is addressed by #3234. FeizaiYiHao's [#3429](https://github.com/verus-lang/verus/pull/3429), **merged November 4**, addresses the second: “Keep the call and give IntoFuture a vstd spec (fixes shape 2 of #3175).” [FeizaiYiHao's closing confirmation](https://github.com/verus-lang/verus/issues/3175#issuecomment-6642261588): “Yes, all fixed.” Neither repair adds a cancellation postcondition.

[#2323](https://github.com/verus-lang/verus/issues/2323), dschoepe's report about passing a future to a function requiring `Send`, is **closed**. tjhance's [#3316](https://github.com/verus-lang/verus/pull/3316), **merged October 26**, says “fixes #2323” and explains: “type-checking the `caller` function will force a borrow-check of `ret42`. This currently causes us to panic.” Its fix integrates mode-checking into rustc's query system. FeizaiYiHao's earlier [#2589](https://github.com/verus-lang/verus/pull/2589) proxy-function approach is **closed without merging**; its proposed restriction on tracked variables across awaits is not evidence of a current blanket prohibition.

[#2521](https://github.com/verus-lang/verus/issues/2521), **closed**, amaurremi, reports early execution of the compiler's body query before Verus erasure is initialized when an external trait returns `impl Future`. [#2514](https://github.com/verus-lang/verus/issues/2514), **closed**, the same reporter, was a dependency-version mismatch: [amaurremi](https://github.com/verus-lang/verus/issues/2514#issuecomment-4616528875) says, “Sorry, you're right it was a mismatch of my dependency versions.” These must not be counted as two current verified Cargo failures.

[#3244](https://github.com/verus-lang/verus/pull/3244), **merged October 16**, tautschnig, replaces a panic involving return-position `impl Trait` in traits with an unsupported-feature error. Author: “A projection on the associated type rustc synthesizes for `-> impl Trait` (or `async fn`) in a trait has no name, and AssocItem::name() panics on it.” That is improved rejection, not support for the feature.

[#3481](https://github.com/verus-lang/verus/pull/3481), **open**, FeizaiYiHao, is current preparatory work for async trait functions: “The future PR for supporting async trait functions depends on this PR.” It removes return types and asyncness from generated trait specification companion functions: “Since the purpose of `VERUS_SPEC__f` is to have a place for `f`'s spec, we now only include the specs in `VERUS_SPEC__f`.” This is evidence of active development, not a promised completion date.

Two additional **open** Drop issues matter for cancellation:

- [#778](https://github.com/verus-lang/verus/issues/778), tjhance: “atomicity-checks don't account for drop calls”. [The 2024 discussion](https://github.com/verus-lang/verus/issues/778#issuecomment-2098929144) says: “This is low-pri while @utaal investigates the possibility of getting drop information from MIR.” A later [remi-delmas-3000 comment](https://github.com/verus-lang/verus/issues/778#issuecomment-6194762365) challenges the proposed soundness argument: “The program below passes the opened permission into `drop`.” The old statement is historical, not evidence that utaal is currently implementing a fix.
- [#2949](https://github.com/verus-lang/verus/issues/2949), tjhance: “I've typically claimed that `external_type_specification` doesn't actually carry any assumptions with it, but this isn't true; it carries the assumption that `Drop` cannot unwind”. The stated alternative is “doing "proper" drop checking and removing the `no_unwind` requirement.” Trusted wrappers around real library types therefore need their destructor assumptions recorded.

## Who is working on what, and why it is difficult

FeizaiYiHao authored the original async implementation, the November future-law and `IntoFuture` repairs, the cross-module repair, and the open trait-specification prerequisite. tjhance supplies architectural review and has implemented fixes for compiler query ordering, lifetime handling, and async return representation. dschoepe authored the draft guide and reported early integration failures. parno and Chris-Hawblitzel reviewed or discussed the original implementation. These are observed contributions, not an organizational ownership claim.

For #3299, [FeizaiYiHao proposed loading separate ghost metadata](https://github.com/verus-lang/verus/issues/3299#issuecomment-6671104146). [tjhance rejected its sufficiency](https://github.com/verus-lang/verus/issues/3299#issuecomment-6671733997): “we also want to support the case where a verified crate is called from an unverified crate. That means the type needs to have the right marker traits even when the erased version is compiled.” [FeizaiYiHao's latest proposal](https://github.com/verus-lang/verus/issues/3299#issuecomment-6808661940) says: “For `async` functions, for each `await` and its tracked witnesses (of type `T`), declare a local variable with type `PhantomData<T>` before `await`, and use it after `await`.” It is a proposal, not a merged fix.

Inference: the gaps are not principally a missing parser keyword. Rust computes opaque future types, captured state, lifetimes, and marker traits through compiler queries; Verus must preserve their meaning through ghost-code erasure. Separately, proving cancellation requires the state and destructor effects at suspension, whereas the current await contract summarizes completion. The upstream evidence establishes active work on the former problems; this search found no dedicated cancellation-verification implementation or announced schedule.

## Search coverage and earlier milestones

Searched all-state GitHub issues and PRs for `async`, `future`, `IntoFuture`, `drop`, and `cancel`, with up to 100 results per broad query; inspected the directly relevant bodies and comments and #1993's reviews. Generic matches about unrelated solver processes, collections, or uses of the word “future” were excluded. This is a reproducible scoped survey, not a guarantee that every relevant discussion uses these words.

Earlier directly related milestones, retained to distinguish predecessors from current limitations:

- [#545](https://github.com/verus-lang/verus/pull/545), merged 2023-04-26, utaal: “ignore OpaqueTy items to support external async functions”.

- [#1785](https://github.com/verus-lang/verus/pull/1785), merged 2025-11-04, FeizaiYiHao: “Add support for Opaque types defined by function returns”.

- [#1839](https://github.com/verus-lang/verus/pull/1839), closed without merging, FeizaiYiHao: “First draft for async function support”.

- [#2081](https://github.com/verus-lang/verus/pull/2081), closed without merging, FeizaiYiHao: “add support for opaque types defined by assume specification”.

- [#2138](https://github.com/verus-lang/verus/pull/2138), merged 2026-03-02, FeizaiYiHao: “add support for opaque types defined by assume specification”.

- [#2376](https://github.com/verus-lang/verus/pull/2376), merged 2026-04-24, tjhance: “new-mut-ref: add test postcondition_missing_old_async_fn”.

- [#2378](https://github.com/verus-lang/verus/pull/2378), merged 2026-04-27, tjhance: “async fns: compute param names before body traversal”.

- [#2321](https://github.com/verus-lang/verus/issues/2321), closed, dschoepe: “Name required for return value of `async fn` returning unit future”.

- [#2459](https://github.com/verus-lang/verus/pull/2459), merged 2026-05-19, tjhance: “remove named return value requirement”.

- [#3015](https://github.com/verus-lang/verus/pull/3015), merged 2026-10-07, tjhance: “refactor async_ret”.

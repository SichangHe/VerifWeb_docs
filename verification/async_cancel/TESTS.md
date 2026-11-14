# Async support probes
(authored by agents unless marked 🧑)

Tested 2026-11-13 with Verus `0.2026.11.05.31e44e6`, release,
one verification thread, Rust toolchain `1.99.1-x86_64-unknown-linux-gnu`.
These are small feature probes, not library verification or cancellation proofs.
Each linked source is the exact input producing the quoted verifier output.

- [basic.rs](probes/basic.rs): async return postcondition and caller assertion after await
  - “verification results:: 2 verified, 0 errors”
- [false_ensures.rs](probes/false_ensures.rs): returns 1 while promising 2
  - “error: postcondition not satisfied”
  - “verification results:: 0 verified, 1 errors”
- [mut_ref.rs](probes/mut_ref.rs): writes through a mutable reference before and after await, proves `*final(x) == 2`, then proves the caller observes 2
  - “verification results:: 3 verified, 0 errors”
- [cross_module.rs](probes/cross_module.rs): another module awaits a public async function and uses its return postcondition
  - “verification results:: 2 verified, 0 errors”
  - this ordinary module boundary is not a reproduction of every reported module-related regression
- [cross_module_create.rs](probes/cross_module_create.rs): the [#3439 reproduction](https://github.com/verus-lang/verus/issues/3439), with an ordinary function creating another module's async future and no async function in the caller module
  - “error: could not find function Fun(Path(vstd, [\"t%future\" :: \"t%FutureAdditionalSpecFns\" :: \"awaited\"]))”
  - this reproduces the reported pruning failure on November 5, unlike the awaiting caller above
- [no_lifetime.rs](probes/no_lifetime.rs): the [#2541 reproduction](https://github.com/verus-lang/verus/issues/2541), both with and without `--no-lifetime`
  - both runs report “verification results:: 0 verified, 0 errors”
  - the reported internal compiler error did not reproduce on November 5
  - the code is outside `verus!`; zero functions were verified, so this tests compiler robustness, not support for verified async trait methods
  - the default run additionally warns “impl trait in impl method signature does not match trait method signature”
- [async_block.rs](probes/async_block.rs): an inline `async { 1u64 }` block
  - “error: Verus does not currently support coroutine types”
- [async_trait.rs](probes/async_trait.rs): async method declaration, implementation, and caller
  - “error: Verus does not currently support `impl Trait` types in trait definitions”
  - rejection occurs at the trait declaration; this does not independently test the implementation body
- [custom_future.rs](probes/custom_future.rs): handwritten `Future::poll` returns `Poll::Ready(7)`; `FutureSpecImpl` defines its result; caller proves await returns 7
  - “verification results:: 2 verified, 0 errors”
  - removing `FutureSpecImpl` produced “error: postcondition not satisfied”, pointing to `future.rs:30:13: 37:15 (#0)`
  - that exploratory failure was an unproved future contract, not unsupported `poll` syntax
- [open_invariant.rs](probes/open_invariant.rs): await inside `open_local_invariant!`, even with the async callee declared `opens_invariants none no_unwind`
  - “error: callee may open invariants disallowed at call-site”
  - “error: cannot show this call will not unwind”
  - “call to core::future::into_future::IntoFuture::into_future might unwind”
  - “unwinding is not allowed in this invariant block”
  - these diagnostics concern invariant-opening and unwind rules, not a drop-at-await proof obligation

- [drop_cleanup.rs](probes/drop_cleanup.rs): verifies a destructor writing through an exclusive reference, with `opens_invariants none no_unwind`
  - “verification results:: 1 verified, 0 errors”
  - this verifies the body, not an implicit-drop postcondition at its caller
- [drop_opens.rs](probes/drop_opens.rs): omits `opens_invariants none` on an otherwise empty destructor
  - “error: a `Drop` implementation must be marked `opens_invariants none`”

Version comparison

- Verus `0.2026.11.02.8bf68ee` also verifies `cross_module.rs`
  - “verification results:: 2 verified, 0 errors”
- that version rejects the same `custom_future.rs`
  - “error[E0405]: cannot find trait `FutureSpecImpl` in module `vstd::future`”
  - this establishes an API difference, not that all handwritten futures were impossible on that version
- both executables emitted the loader warning “weak version `GLIBC_2.39' not found” but continued to perform verification

Reproduction

Set `VERUS` to the verifier executable and, if necessary, `VERUS_Z3_PATH` to Z3.
Run `bash verification/async_cancel/probes/run.sh` from the repository root.
The runner checks expected success or failure and diagnostic text, prints only
unexpected results, uses one thread, and removes its temporary logs.
The entire runner passed against the November 5 version.
For a version fixing #3439, set `EXPECT_CROSS_MODULE_CREATE_EXIT=0` to expect
successful verification of that reproduction.

Test design

- each file isolates one feature, with the false postcondition as a negative control
- accepted probes check ordinary completion contracts
- rejected probes retain the exact construct under test
- the custom future supplies its specification and verifies its implementation
  - no `external_body`, `assume`, or unchecked future implementation
- an early invariant probe destructured `Tracked` in the async parameter
  - it produced “error: Verus internal error: ill-formed `unwrap_parameter` header”
  - moving extraction into the function body allowed the intended await check
  - that incidental internal error is not evidence that await itself is unsupported

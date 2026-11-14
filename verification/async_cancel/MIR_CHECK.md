# Checking the real compiler-generated cancellation path
(authored by agents unless marked 🧑)

result
- `check_drop_paths.py` checks a control-flow fact about the real Pingora PR #1037 compiler output
  - output: `variant 7 slot 8: every normal return follows successful guard-slot drop`
  - four other suspension variants report `no CacheLockGuard slot; no cleanup claim`
  - the slot has type `Option<CacheLockGuard>`, so dropping it does not establish that it held `Some`
- this is a checked connection to compiled production code, not a proof of cancellation safety
  - no separate application state machine replaces the Rust body
  - compiler output and the Python parser/checker are trusted
  - no Verus proof of the cleanup body is provided by this experiment

method
- read paired `coroutine_resume` and `coroutine_drop` dumps for the same function
  - require entry to read the frame discriminant and immediately switch on that value
  - obtain suspended-state field positions from the compiler's layout
  - obtain destruction entry blocks from its discriminant switch
- explore every graph path using states `(basic block, guard-slot drop completed)`
  - before completion, accept only storage bookkeeping, boolean flag writes outside the guard slot, direct frame-field drops and branches
  - reject guard-slot overwrites, exposed aliases and other instructions
  - assume other fields' destructors respect Rust aliasing and cannot mutate this private guard slot
  - mark completion only on the guard drop's normal-return edge
  - follow both normal and unwind successors
  - reject any normal return reached without completion
  - distinguish return and unwind edges even when they target the same block
  - reject checks with no guard slot or no reachable normal return
- branches are explored without using their conditions
  - this can reject infeasible paths but does not omit a recognized graph edge
  - nontermination, panic propagation, and process abort make no normal-return promise
  - input is pinned rustc text, not a stable interchange format or an adversarial-input certificate
  - function names are checked, but build identity must be ensured by generating both files together

reproduction
- generate Pingora dumps using [real_pingora/README.md](real_pingora/README.md)
- from the repository root, run
  - `uv run --no-project python verification/async_cancel/check_drop_paths.py RESUME.mir DROP.mir --guard CacheLockGuard`
- validate parser/checker mutations with actual compiler output
  - `PINGORA_MIR_DIR=YOUR_DUMP_DIRECTORY uv run --no-project python -m verification.async_cancel.test_drop_paths`
  - the small fixture is compiled with Rust 1.99.1
  - the real Pingora dump is also checked when the environment variable is supplied
  - removing the normal guard-drop edge is rejected in both
  - mismatched functions, absent guard, unsupported terminator, and a shared normal/unwind target are rejected
  - replacing the live guard with None or borrowing its slot before dropping it is rejected
- executed test output: `Ran 2 tests in 0.060s` followed by `OK`
  - real Pingora bypass mutation was rejected
  - Ruff and basedpyright reported no findings

remaining proof obligations
- follow-up audits are recorded in [ownership](OWNERSHIP_MIR.md) and [cleanup](CLEANUP_MIR.md)
  - audit fingerprints detect changes to reviewed fragments; they do not discharge semantic proof obligations
  - the [semantic translator](CLEANUP_SEMANTICS.md) now generates and discharges destructor map-effect obligations under explicit compiler, translator and dependency assumptions
- establish that publishing a writer lock initializes this slot to `Some` with that same lock
  - a type-correct but empty guard slot would pass this control-flow check
- verify the real destructor's notification and conditional removal
  - the semantic translator handles acyclic normal-call paths; no unwind-completion or termination claim
  - retain its dependency assumptions explicitly
  - `Arc::ptr_eq` currently produces `is not supported` in a direct Verus probe
- prove or state the behavior of callback destruction and lock acquisition
  - the compiler drops the child lookup future before the guard
  - cleanup need not complete if that destructor blocks or aborts
- account for every writer state and source-to-compiler transformation
  - this check detects guard-carrying states; it does not prove that every writer state carries a guard
- do not relax Verus's destructor restrictions alone
  - [well_formed.rs](https://github.com/verus-lang/verus/blob/6ae5f7b97c6403789fc1f12117ea8b2f0092289c/source/vir/src/well_formed.rs#L1737-L1758) requires `opens_invariants none` and `no_unwind`
  - changing this requires checking effects at implicit destructor calls
  - [vstd RwLock](https://github.com/verus-lang/verus/blob/6ae5f7b97c6403789fc1f12117ea8b2f0092289c/source/vstd/rwlock.rs#L369-L386) warns: `Verus does not check that lock is released.`
  - replacing the production lock with vstd's lock therefore does not establish cancellation cleanup

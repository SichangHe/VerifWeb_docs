# Conditional publication dataflow interpreter
(authored by agents unless marked 🧑)

scope
- `publication_mir.py` interprets actual Pingora get-resume MIR and its concrete guard constructor
  - conditional entry at bb14 with the frame's self and hashed key already initialized
  - HashMap get returns None, calls and drops return normally, callback polls return Pending
  - pending callback polls preserve the historical inserted allocation, map and key in a Some guard
  - one interpreted state-7 resume cycle reproduces the complete retained frame environment
    - the same transition can repeat, with fresh poll context and discarded locals
- no fingerprints or accepted-block instruction templates
  - interpreter follows actual branch targets and resolves operands, borrows, tuple projections, Option discriminants, closure captures and frame assignments
  - the concrete constructor is interpreted with actual captures and Arc argument
  - unsupported executed statements, calls, argument sorts and cycles reject
- this does not establish all-entry or all-publication coverage
  - fixed entry, frame schema and resume state remain explicit scope restrictions
  - Ready, unwind, map-hit and cleanup paths are outside the interpreted path
  - no assertion about Pending reachable after a Ready callback result
  - no independent proof of the Python interpreter or Rust semantics

state and calls
- symbolic values distinguish Arc allocations, map identity, hashed key, references, tuple members, Option variants and guards
- insert records its actual map/key/Arc triple
  - Some guard at Pending must contain exactly that triple
  - concurrent replacement of the map entry is allowed
- explicit trusted normal-return contracts
  - write/Deref/DerefMut preserve protected map identity
  - new_arc produces a fresh allocation; clone preserves its identity
  - HashMap get follows the stated map-miss condition; insert publishes its passed value
  - Option as_ref/map preserve variant and apply the interpreted closure to Some
  - lookup/IntoFuture/Pin construct the callback future; poll may return Pending without modifying unrelated private frame storage
- calls reject wrong argument identities or sorts where the contract requires them
  - opaque calls are unsupported
  - dropping a guard or changing its slot before Pending rejects
  - StorageLive/StorageDead clear local knowledge
  - copy and move have equal value propagation
    - valid compiler MIR supplies move legality; this is not a Rust borrow checker
    - moves of a guard or any aggregate containing one reject rather than leave stale guard initialization

trusted input
- paired well-typed compiler-generated MIR from the same pinned build described in [real_pingora/README.md](real_pingora/README.md)
  - expected compiler block formatting and hard-coded get frame schema
  - local declaration types and coroutine layout are not revalidated
  - constructor closure identity is matched against the call and captures
  - `_0`, `_1`, `_2` retain Rust return/parameter conventions
- safe Rust aliasing and standard library contracts
  - private guard slots cannot be mutated through callback arguments
- initial frame fields denote the actual self, lookup key, hashed key and extra argument

validation
- export `PINGORA_RESUME_MIR` and `PINGORA_EMITTED_MIR` to the paired real artifacts
- run from the repository root
  - `uv run --no-project python -m verification.async_cancel.publication_mir "$PINGORA_RESUME_MIR" "$PINGORA_EMITTED_MIR"`
  - `uv run --no-project python -m verification.async_cancel.publication_mir_test`
- tests use actual artifacts, mutate instructions in memory, and accept neutral local renaming
  - reject different allocation, missing Some, swapped tuple, wrong reader branch, construction bypass, guard disarming before Pending or on resumption, wrong state/key capture, unsupported rvalue and wrong constructor lock
  - moving the saved guard out before Pending rejects
  - malformed/type-invalid mutants test rejection behavior, not newly compiled Rust regressions

next obligation
- interpret both poll outcomes and all map-hit branches, derive the frame schema, and establish entry/publication coverage before calling this a whole-function conformance check

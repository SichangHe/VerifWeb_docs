# Conditional publication dataflow interpreter
(authored by agents unless marked 🧑)

scope
- `publication_mir.py` interprets actual Pingora get-resume MIR and its concrete guard constructor
  - initial state 0 enters actual bb0 dispatch and bb444, deriving saved self/key/extra and hashed key from executed operands through bb14
  - enumerate all eight Some/None schedules for MemoryCache get and the two HashMap gets
    - stop a case without publication only when structural coverage proves its current block cannot reach the sole direct insert
    - unused suffix choices duplicate cases that exit earlier
  - calls and drops return normally, callback polls return Pending
  - pending callback polls preserve the historical inserted allocation, map and key in a Some guard
  - one interpreted state-7 resume cycle reproduces the complete retained frame environment
    - the same transition can repeat, with fresh poll context and discarded locals
- publication path uses no fingerprints or accepted-block instruction templates
  - interpreter follows actual branch targets and resolves operands, borrows, tuple projections, Option discriminants, closure captures and frame assignments
  - the concrete constructor is interpreted with actual captures and Arc argument
  - unsupported executed statements, calls, argument sorts and cycles reject
- this does not establish all-entry or all-publication coverage
  - checked compiler layout and initial Unresumed state remain explicit scope restrictions
  - hit branches are interpreted through their separating dispatch; their insertion-free suffix behavior is not interpreted
  - Ready, unwind and cleanup behavior remain outside this dataflow interpretation
  - structural checks separately exclude a normal Ready-to-Pending path
  - coverage concerns direct HashMap insertion; effects hidden inside calls are outside this claim
  - no independent proof of the Python interpreter or Rust semantics

state and calls
- symbolic values distinguish Arc allocations, map identity, hashed key, references, tuple members, Option variants and guards
- insert records its actual map/key/Arc triple
  - Some guard at Pending must contain exactly that triple
  - concurrent replacement of the map entry is allowed
- explicit trusted normal-return contracts
  - MemoryCache get reads the actual self cache and lookup key, returning None or Some symbolic T and opaque status
  - hash_one reads that cache's hasher and the lookup key, returning its symbolic hashed key
  - read/Deref preserve protected map identity; cloned preserves None or the existing Arc identity in Some
    - these prefix summaries require no existing publication obligation
  - write/Deref/DerefMut preserve protected map identity
  - new_arc produces a fresh allocation; clone preserves its identity
  - HashMap get returns None or Some reference to a symbolic existing Arc; insert publishes its passed value
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
  - expected compiler block formatting, truthful debug metadata and capture-aggregate field ordering
  - factory signature and actual capture operands are checked against raw debug projections
    - supported factory directly returns one capture aggregate from its typed parameters
  - relevant saved debug identities/types/projections are checked against coroutine field and variant declarations
    - self, key, ttl, extra, hashed_key and guard
    - initial discriminant and guard slot/state are read from metadata
  - other local declaration types, all physical layout details and ABI validity are not independently proved
  - constructor closure identity is matched against the call and captures
  - `_0`, `_1`, `_2` retain Rust return/parameter conventions
- safe Rust aliasing and standard library contracts
  - private guard slots cannot be mutated through callback arguments
- initial capture values come from the checked factory operands
  - saved variant values and hashed key are derived by interpretation, not seeded

validation
- export `PINGORA_RESUME_MIR` and `PINGORA_EMITTED_MIR` to the paired real artifacts
- run from the repository root
  - `uv run --no-project python -m verification.async_cancel.publication_mir "$PINGORA_RESUME_MIR" "$PINGORA_EMITTED_MIR"`
  - `uv run --no-project python -m verification.async_cancel.publication_mir_test`
- tests use actual artifacts, mutate instructions in memory, and accept neutral local renaming
  - reject different allocation, missing Some, swapped tuple, wrong reader branch, construction bypass, guard disarming before Pending or on resumption, wrong state/key capture, unsupported rvalue and wrong constructor lock
  - moving the saved guard out before Pending rejects
  - wrong initial dispatch, saved self/key/extra, hash key and cache-get arguments reject
  - all eight schedules checked; only all-miss publishes in the original artifact
  - swapping the initial map hit/miss targets preserves this cancellation property and is accepted
  - adding a hit-to-insert route rejects through structural coverage
  - changed guard declaration/layout/debug identity, raw key projection and factory key operand reject
  - consistent raw capture reordering, guard-slot reordering and suspension-state renumbering are accepted
  - malformed/type-invalid mutants test rejection behavior, not newly compiled Rust regressions

next obligation
- interpret Ready/unwind/cleanup behavior and account for implicit call effects before calling this whole-function conformance

# Conditional Pingora cancellation check
(authored by agents unless marked 🧑)

run
- prefer [build and check](real_pingora/BUILD_CHECK.md), which directs one compilation's outputs into fresh paths before checking them
- generate resume, drop and whole-crate MIR together using [the pinned build](real_pingora/README.md)
- `uv run --no-project python -m verification.async_cancel.check_pingora RESUME.mir DROP.mir CRATE.mir VERUS`
  - generated proofs go into a temporary directory and are deleted
  - rejects if any constituent check or Verus fails

checked connection
- [structural coverage](ENTRY_COVERAGE.md) checks a unique normal-control-flow prefix from initial dispatch to the sole direct insertion
  - the combined command requires the interpreter's executed prefix to match it
  - callback Ready branches cannot reach another Pending or insertion on normal edges
  - a shared block sequence can carry different values; these graph facts alone do not establish semantic branch coverage
- [publication interpretation](PUBLICATION_MIR.md) tracks the registered map/key/lock identity into the saved guard
  - starts at the compiler's initial dispatch, derives saved captures and the hashed key, and enumerates all eight cache/map hit-or-miss schedules
  - cases leaving the insertion-reaching prefix before publication cannot reach the sole direct insertion
  - publishing cases follow normal-return calls and Pending polls
  - resumed Pending transitions preserve that abstract guard invariant
  - [generated ownership obligations](OWNERSHIP_OBLIGATIONS.md) expose actual interpreted values and resume equations to Verus
  - Verus proves the initial match and preservation, with induction over arbitrary numbers of Pending polls
  - the generator does not assume the former Python ownership postcondition checks succeeded
  - capture operands and saved guard positions are cross-checked against the compiler's factory, debug projections and typed coroutine layout
  - Pingora's own lock-allocation body is interpreted to establish its fresh, zero-permit allocation contract
- [drop instruction analysis](MIR_CHECK.md) restricts operations that could change this same slot before destruction
  - [generated destruction proof](DROP_OBLIGATIONS.md) gives Verus every extracted edge and a candidate invariant
  - Verus checks initialization, edge preservation and return safety, then proves the property for arbitrary finite paths by induction
  - Python's reachable-state computation proposes the invariant; its safety conclusion is not a proof assumption
- [cleanup translation](CLEANUP_SEMANTICS.md) derives Verus obligations from the actual guard destructor
  - its locked map snapshot loses the owner's entry, preserves any replacement and leaves other keys unchanged
  - notification precedes map-lock acquisition
  - the map property holds immediately before releasing the map lock

composition assumptions
- every poll before cancellation returns Pending; no polling after Ready
- direct frame-state writes never restore Unresumed, and every normal return crosses a supported noninitial state write
  - checked across parsed resume code, including otherwise uninterpreted suffixes
  - still assumes valid compiler MIR and no unmodeled raw or aliased whole-frame replacement
  - insertion-free suspended paths therefore cannot later reach insertion without violating the checked unique prefix

limits
- inherits the constituent checks' trusted compiler, parser/interpreter, field-layout, safe-aliasing and dependency-contract assumptions
  - ownership obligations prove the translated abstract equations, not correctness of the Python interpreter or its abstraction of callback state
  - direct artifact input requires files from the same pinned build; the build wrapper prevents stale-file selection but does not authenticate source or compiler
  - Rust's Option destruction must call the selected CacheLockGuard destructor when the saved slot is Some
- no all-entry or whole-function theorem
  - compiler metadata and capture-field ordering remain trusted despite cross-checks; insertion-free suffixes of hit paths and Ready paths remain outside publication interpretation
  - no panic-completion, termination, waiter progress or post-release map-state guarantee
  - successful checks do not establish unconditional library cancellation safety

validation
- [compiled Rust mutations](real_pingora/SOURCE_MUTATIONS.md) test guard removal before await and reversed destructor ownership comparison
  - both reject; direct artifact input still requires the caller to select matching files

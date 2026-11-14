# Conditional Pingora cancellation check
(authored by agents unless marked 🧑)

run
- generate resume, drop and whole-crate MIR together using [the pinned build](real_pingora/README.md)
- `uv run --no-project python -m verification.async_cancel.check_pingora RESUME.mir DROP.mir CRATE.mir VERUS`
  - generated proofs go into a temporary directory and are deleted
  - rejects if any constituent check or Verus fails

checked connection
- [publication interpretation](PUBLICATION_MIR.md) tracks the registered map/key/lock identity into the saved guard
  - starts at the documented map-miss entry and follows normal-return calls and Pending polls
  - resumed Pending transitions preserve that abstract guard invariant
- [drop analysis](MIR_CHECK.md) checks that this same slot is preserved until its successful destruction on every normal-return cancellation path
- [cleanup translation](CLEANUP_SEMANTICS.md) derives Verus obligations from the actual guard destructor
  - its locked map snapshot loses the owner's entry, preserves any replacement and leaves other keys unchanged
  - notification precedes map-lock acquisition
  - the map property holds immediately before releasing the map lock

limits
- inherits all three checks' trusted compiler, parser/interpreter, field-layout, safe-aliasing and dependency-contract assumptions
  - artifacts must come from the same pinned build; the command does not authenticate their provenance
  - Rust's Option destruction must call the selected CacheLockGuard destructor when the saved slot is Some
- no all-entry or whole-function theorem
  - initial frame facts, map-hit and Ready paths remain outside publication interpretation
  - no panic-completion, termination, waiter progress or post-release map-state guarantee
  - successful checks do not establish unconditional library cancellation safety

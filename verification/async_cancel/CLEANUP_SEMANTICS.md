# Translating destructor MIR into map obligations
(authored by agents unless marked 🧑)

purpose
- 🧑 “the human requires proving the real code conforms to the spec, not only a model”
  - requirement relayed by the parent agent for this implementation
- [translator](cleanup_semantics.py) symbolically executes the actual Pingora destructor and its closure
  - replaces the fingerprint-to-manual-audit correspondence with executable translation
  - does not independently prove the translator correct

translation
- extracts exactly one destructor and one predicate closure from compiler text
- parses basic blocks, rejects unsupported instructions and cycles
- starts destructor argument `_1` as the guard being destroyed
  - tracks local aliases and projections into lockers, key and Arc owner
  - distinguishes the owned write guard from borrowed references; dropping a reference cannot release the lock
  - closure starts with its capture and the entry passed by `is_some_and`
- applies explicit contracts to recognized dependency calls and checked operand sorts
  - Arc comparison becomes equality of the actual symbolic operands
  - lookup records the current symbolic map and supplied key
  - `is_some_and` combines membership with the translated closure result
  - removal changes the symbolic map at its actual supplied key
- explores both boolean successors with their actual edge conditions
  - follows goto edges independently of block numbers
  - requires notification before acquisition and guard release before normal return
- emits one Verus proof per normal return path
  - path condition implies translated map effect equals `cleanup(before, key, owner)`
  - imports the existing [abstract contract](cleanup_contract.rs) into the temporary proof
  - `before` denotes the map at exclusive write-lock acquisition
  - equality entails the existing abstract preservation and removal properties
- translation success alone is not verification success
  - generated obligations must also pass Verus

trusted boundary and limits
- source provenance, Rust compiler, well-typed MIR input and field layouts
  - guard fields 0/1/2 mean lockers/key/owner; lock field 1 means semaphore
  - local declarations are recognized syntactically, not type checked independently
- Python extraction, parser, symbolic interpreter and Verus source generation
  - narrow supported syntax is deliberately incomplete
  - finite acyclic normal paths only; panic and unwind completion are outside the claim
  - unvisited blocks admit only restricted cleanup syntax
- dependency contracts, rather than dependency implementation proofs
  - Arc dereference preserves identity; `ptr_eq` compares allocation identities
  - write acquisition supplies exclusive access to the same map until guard destruction
  - HashMap lookup and removal use the supplied u64 key with ordinary equality and hashing
  - `is_some_and` invokes the captured closure iff the option is present
  - Arc destruction does not alter this map; write-guard destruction releases its lock
  - returned `add_permits(10)` adds ten permits to the guard owner's semaphore
- specification concerns the map immediately before lock release
  - concurrent changes after release are unrestricted
  - no termination, cancellation-delivery, wakeup or semaphore-count guarantee
  - caller guard construction and actual destruction remain separate obligations

reproduce from repository root
- obtain real crate MIR using [build instructions](real_pingora/README.md)
- generate outside the repository
  - `uv run --no-project python -m verification.async_cancel.cleanup_semantics CRATE.mir /tmp/cleanup-proof.rs`
  - `verus --num-threads 1 /tmp/cleanup-proof.rs`
- [integration tests](cleanup_semantics_test.py)
  - `uv run --no-project python -m verification.async_cancel.cleanup_semantics_test CRATE.mir VERUS`
  - actual crate verifies three proof functions: abstract contract and two translated paths
  - renumbered locals and an equivalent CFG with an extra goto verify
  - reversed identity branch, constant wrong removal key and identical pointer-comparison operands translate but fail map postconditions
  - unsupported instruction, changed permit count and missing guard release fail translation
  - dropping a borrowed write guard instead of its owner fails translation
  - mutants are edited MIR text, not compiled Rust source variants
  - temporary generated proofs are deleted; the script reports failures only

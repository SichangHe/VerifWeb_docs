# Cancellation CFG obligations
(authored by agents unless marked 🧑)

purpose
- 🧑 “the human requires proving the real code conforms to the spec, not only a model”
- generate Verus obligations directly from the paired compiler cancellation CFG
  - `generate(resume, drop, variant, slot)` returns Verus items or an unsupported-input error
  - selected slot must occur as CacheLockGuard in the paired suspended-state layout
  - embed returned items inside the existing cleanup proof's `verus!` module

proof
- state is `(basic block, successful guard drop completed)`
- extracted edges include normal and unwind successors of every parsed block
  - only the selected guard drop's normal-return edge sets completion
  - completion remains true thereafter
- Python proposes the finite set of reachable states as an invariant certificate
  - does not call the Python safety checker or reject an incomplete normal return
- Verus independently proves initial membership, preservation for every extracted edge and completion at every invariant normal-return state
- recursive proof over an arbitrary sequence index establishes the invariant and return safety for every finite path
  - no fixed path-length bound or assumed checker-success predicate
  - loops are covered; termination and eventual return are not claimed
- a reachable normal return is required to reject vacuous certificates

trusted boundary
- paired valid compiler MIR, compiler field layouts, dispatch semantics and Python extraction
- shared parser `check_drop_paths.blocks` and instruction filter `preserve_guard`
  - before completion, rejects unsupported slot changes and exposed aliases
  - other field destructors obey safe Rust aliasing and cannot modify the private guard slot
- Python translates syntax and proposes the invariant; Verus checks its inductiveness and safety
  - no proof that extraction faithfully represents Rust semantics
- successful slot destruction invokes the destructor only if the slot contains Some
  - publication and Option destruction supply this separate connection
- cleanup effects and matching guard ownership are separate obligations

validation
- run `uv run --no-project python -m verification.async_cancel.drop_obligations_test RESUME.mir DROP.mir VERUS`
  - requires the actual pinned Pingora artifacts and actual Verus executable
  - real cancellation CFG verifies
  - replacing its guard drop with a goto still translates but fails the Verus return-safety postcondition
  - temporary generated proofs are deleted; verifier uses one thread

# Restricted ownership correspondence check
(authored by agents unless marked 🧑)

scope
- follow-up: [publication interpretation](PUBLICATION_MIR.md) now propagates operands through the conditional map-miss and repeated-Pending path instead of matching these fingerprints
- `ownership_mir.py` recognizes one reviewed MIR fragment from Pingora PR #1037, Rust 1.99.1
  - it compares complete blocks and the complete concrete constructor, ignoring only indentation and empty lines
  - `ownership_mir_pattern.py` records SHA-256 fingerprints of the reviewed blocks and constructor
  - assumes SHA-256 collision resistance
  - this is an audit fingerprint with a manually justified argument, not a symbolic interpreter or a machine-checked proof of Rust semantics
  - unrelated changes can pass; any change within the accepted fragment fails until reviewed
- the conditional claim starts at `get` block bb14 and takes its map-miss path
  - normal call returns lead to a registered Arc and a matching `Some` guard at the callback's Pending return
  - later Pending polls retain that guard
  - Ready and unwind edges leave this argument's scope
  - other writer paths, arbitrary entry into the fragment, and later operations after Ready are not certified

argument
- bb14 acquires `self.lockers`; bb28–30 looks up the saved key
  - the absent-key branch reaches bb31, which creates allocation A
- bb45 clones A; bb46–47 inserts that clone under the saved key into the locked map
  - bb49–50 puts the original A in `Some` and the reader option in `None`
  - bb57 moves these correlated values into fields 6 and 7
  - bb58 selects bb180 because the reader is None
  - the nonselected reader branch is not treated as feasible for this path
- bb180 borrows the writer option; bb182 maps it with the concrete guard constructor
  - the constructor clones its Arc argument and copies the captured map reference and key
  - therefore field 8 is Some with the same historical inserted allocation, key and map
  - another thread may already have replaced the map entry
- bb183–192 constructs and polls the callback, retaining field 8 through Pending
  - the only mutable frame-field borrow passed to polling targets child-future field 9
  - bb192 stores state 7 and returns Pending
  - state-7 dispatch bb0 → bb441 → bb193 → bb186 repeats polling without reconstructing or disarming the guard

evidence
- in the pinned `coroutine_resume` artifact, bb49 says `_78 = Option::<Arc<CacheLock>>::Some(move _79);`
- bb50 says `_33 = (move _78, move _80);`, after assigning `_80 = Option::<Arc<CacheLock>>::None;`
- the emitted `get::{closure#0}::{closure#0}` says `_5 = <Arc<CacheLock> as Clone>::clone(copy _2) -> [return: bb1, unwind continue];`
  - its bb1 says `_0 = CacheLockGuard::<'_> { lockers: copy _3, hashed_key: move _4, lock: move _5 };`
- artifact generation and source attribution are in [real_pingora/README.md](real_pingora/README.md)
  - constructor source is the closure at `read_through.rs:282:48`
  - regenerate the MIR to inspect the complete statements and successors identified by the fingerprints

trusted boundaries
- both artifacts must come from the same pinned build
  - names and constructor identity are checked, but build identity is supplied by the caller
- assume compiler MIR accurately describes safe Rust execution and its documented Option/Poll discriminants
- assume Arc cloning preserves allocation identity; Option as_ref/map have their standard semantics
- assume parking_lot write/Deref/DerefMut refer to the same protected map and HashMap insert publishes the passed value
- assume opaque calls obey Rust aliasing and do not mutate the private guard/writer frame slots
  - callback mutations of shared map contents remain allowed
- no cleanup-body correctness or completion is established here
  - combine this conditional ownership relation with the separate destructor-body and drop-path checks only under their stated assumptions
  - panics between insertion and guard construction need separate analysis
- parser and manually reviewed pattern are trusted
  - no claim about adversarial text, arbitrary Rust, all publication paths, termination, or an independently proved certificate checker

run
- set `PINGORA_RESUME_MIR` to the real get coroutine_resume dump
- set `PINGORA_EMITTED_MIR` to the same build's emitted crate `.mir` file
- from the repository root
  - `uv run --no-project python -m verification.async_cancel.ownership_mir "$PINGORA_RESUME_MIR" "$PINGORA_EMITTED_MIR"`
  - `uv run --no-project python -m verification.async_cancel.ownership_mir_test`
- mutation checks reject changed insertion identity, missing Some, swapped tuple fields, wrong branch selection, wrong capture, skipped construction, guard disarming, changed resumption and layout, and changed constructor identity/key/map
  - these are checker-input mutations, not newly compiled Rust regressions

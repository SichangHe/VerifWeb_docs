# Ownership obligations from actual MIR
(authored by agents unless marked 🧑)

purpose
- `ownership_obligations.generate(resume, emitted)` returns Verus items and an error
  - include successful items inside a `verus!` module importing `vstd::prelude::*`
  - generation does not call Python `check` or `check_case` ownership postcondition checks
- retain structural coverage, compiler-layout and allocation-contract validation from `prepare`
- enumerate actual cache/map outcomes with `trace_case`
  - retain both actual interpreter outputs, even if a guard is wrong or disarmed
  - no-publication cases require the existing graph justification
  - unsupported syntax and guard moves still reject during translation

generated equations
- encode actual inserted map/key/Arc and saved guard as distinct structured terms
  - variant tags distinguish scalar and aggregate sorts
  - preserve aggregate labels as well as members
  - map/key/allocation and other opaque identities are arbitrary integer parameters
  - different fresh allocations are unequal under the derived Arc allocation contract
  - no premise assumes guard equality or a successful ownership check
- encode retained abstract frame slots, state discriminant, publication identity, return outcome and lock state
- emit one family of items per publishing outcome
  - `_initial` is the actual first output
  - `_next` contains actual resume-output slot equations
    - unchanged abstract terms read the corresponding input slot
    - changed or uninitialized terms appear explicitly in the output
  - `_invariant` requires the initial abstract frame shape and matching published guard, Pending outcome, expected suspension state and released map lock
  - `_base` proves the first output satisfies that invariant
  - `_step` proves one interpreted resume preserves it
  - `_pending_induction` proves preservation for every natural number of subsequent Pending polls

trusted translation boundary
- `_next` describes only inputs in its generated invariant family
  - it is not a general MIR evaluator for arbitrary frames
  - equality to `_initial` fixes the supported abstract frame shape while leaving symbolic identities arbitrary
  - lifting the trace to arbitrary identities relies on interpreter operations depending only on tracked sorts, constructors and alias identities
  - both lookup variants are enumerated; callback polls remain conditional on Pending
- retained frame equality concerns the interpreter's abstract values
  - an opaque child future may mutate its internal state while preserving its abstract capability to be polled
  - its internal heap state is not asserted unchanged
  - private guard slots remain protected by the existing aliasing and callback contracts
- parser, symbolic interpretation, symbol substitution and Verus source generation remain trusted
  - compiler/dependency assumptions remain those of [publication interpretation](PUBLICATION_MIR.md)
  - no independent soundness proof of this translator, Ready/unwind theorem, child-drop progress claim or whole-library guarantee

validation
- run `uv run --no-project python -m verification.async_cancel.ownership_obligations_test RESUME.mir CRATE.mir VERUS`
- actual pinned artifacts and neutral local renaming translate and verify
- changed clone-to-new allocation and initial/resumed guard-disarming mutants translate but fail Verus ownership postconditions
  - distinguishes semantic proof failure from unsupported-input rejection
- unknown MIR rvalue rejects translation
- generated proof files remain temporary and are deleted

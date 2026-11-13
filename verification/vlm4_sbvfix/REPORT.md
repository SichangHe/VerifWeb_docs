# smallbitvec ptr::add spec fix
(authored by agents unless marked 🧑)

Result: the unsound trusted spec is replaced; the counterexample no longer verifies; the full proof re-verifies unchanged in scope (96 verified, 0 errors).

## Rust contract (quoted from cx_servo/SMALLBITVEC_REVIEW.md, citing doc.rust-lang.org pointer::add)
“The offset in bytes, count * size_of::<T>(), computed on mathematical integers (without ‘wrapping around’), must fit in an isize.” “Let result be self.addr() + count * size_of::<T>(), computed on mathematical integers. This must fit in a usize.” “If the computed offset is non-zero, then self must be derived from a pointer to some allocation, and the entire memory range between self and result (i.e., self.addr()..result) must be in bounds of that allocation.”

## Change (sbv_full.rs)
- removed `assume_specification [<*mut T>::add]` (it allowed result addr == usize::MAX + 1)
- added trusted `#[verifier::external_body] fn ptr_add<T>(p, i, Tracked<&Dealloc>)` whose body is `p.add(i)`; requires:
  - `i * size_of::<T>() <= isize::MAX`
  - `p@.addr + i * size_of::<T>() <= usize::MAX`
  - `p@.provenance == d.provenance()` and `d.addr() <= p@.addr <= result <= d.addr() + d.size()` (allocation bounds via the vstd `Dealloc` token for the live allocation)
  - this is stricter than Rust's contract (bounds required even for zero offset), so it is sound w.r.t. it
- 6 call sites switched to `ptr_add(..., Tracked(&dealloc / &h.dealloc))`; one loop invariant in heap allocation gained the `dealloc` addr/size/provenance facts. No other proof edits were needed.

## Evidence
- `verus --crate-type=lib sbv_full.rs` → “verification results:: 96 verified, 0 errors” (full.log)
- counterexample ported to the new API (contradiction_fixed.rs: p@.addr == 1, ptr_add(p, usize::MAX)) → “error: precondition not satisfied”, “96 verified, 1 errors” (contradiction_fixed.log). The original file's direct `p.add(...)` call has no spec anymore, so it is not callable from verified code at all.

## What still holds / remaining caveats (unchanged from cx_servo review)
- all previously reported functional contracts still verify
- still trusted: `ptr_add` (now matching the documented contract) and vstd
- still a bounded rewritten model, not upstream smallbitvec; unported ops and bounds listed in cx_servo/REVIEW.md item 2 remain

# Smallbitvec proof audit
(authored by agents unless marked 🧑)

The original pointer specification is unsound. The corrected wrapper and inline-only model have no discovered inconsistency. “Sound” below means no issue found within the declared model and target assumptions, not a proof that the verifier or upstream library is sound.

## Reproduction and per-file results

Reran every listed file with `tools/verus-x86-linux/verus --crate-type=lib FILE`. Fresh logs are under [sbv_logs](sbv_logs), named by replacing each slash after `out/` with an underscore and appending `.log`. Counts below quote the verifier's `verification results::` output (verified, errors). All paths are relative to the workspace.

- `out/cx_servo/sbv_work/heap.rs`: “20 verified, 0 errors”; unsound; trusted old pointer spec and layouts.
- `out/cx_servo/sbv_work/sbv_full.rs`: “96 verified, 0 errors”; unsound; same trusted items.
- `out/cx_servo/sbv_work/trusted_add_contradiction.rs`: “97 verified, 0 errors”; unsound; same trusted items; successful contradiction witness.
- `out/cx_servo/sbv_work/neg1.rs`: “19 verified, 1 errors”; rejected negative test; its trusted old pointer spec remains unsound. Wrong deallocation size is rejected.
- `out/cx_servo/sbv_work/neg2.rs`: “19 verified, 1 errors”; rejected negative test; its trusted old pointer spec remains unsound. Writing the unchanged word fails the sequence-update assertion.
- `out/cx_servo/sbv_work/copy_zero.rs`: “95 verified, 1 errors”; rejected negative test; its trusted old pointer spec remains unsound. Copying zero words fails preservation during reallocation.
- `out/cx_servo/sbv_work/u1.rs`: no verified count; rejected before verification, “error: aborting due to 5 previous errors”; unsupported API experiment, no custom trusted items. No sound-proof verdict is applicable.
- `out/vlm4_sbvfix/sbv_full.rs`: “96 verified, 0 errors”; sound within the bounded rewritten model; trusted `ptr_add` external body and layouts.
- `out/vlm4_sbvfix/contradiction_fixed.rs`: “96 verified, 1 errors”; rejected contradiction test; corrected trusted wrapper appears sound. The attempted overflowing call fails its precondition.
- `out/vlm_servo/smallbitvec/sbv.rs`: “46 verified, 0 errors”; sound within the inline-only model; trusts the declared 64-bit target, no custom assumed specification or external body.

`results.json` records byte-identical aliases under `out/vlm3_servo/smallbitvec_heap/`: `heap.rs`, `sbv_full.rs`, `neg1.rs`, `neg2.rs`, and `u1.rs`. Their respective verdicts and trusted items are identical.

## Unsound old pointer specification

[Old full model](../cx_servo/sbv_work/sbv_full.rs), lines 166–168, says:

```rust
pub assume_specification<T> [<*mut T>::add] (p: *mut T, i: usize) -> (r: *mut T)
    requires p@.addr + i * size_of::<T>() <= usize::MAX + 1,
    ensures r@.addr == p@.addr + i * size_of::<T>(), r@.provenance == p@.provenance, r@.metadata == p@.metadata;
```

The same declaration occurs at lines 11–13 in the heap and negative heap files, and lines 166–168 in `copy_zero.rs` and `trusted_add_contradiction.rs`. It permits an unrepresentable pointer address. The [existing witness](../cx_servo/sbv_work/trusted_add_contradiction.rs) ends with:

```rust
fn trusted_add_contradiction(p: *mut u8)
    requires p@.addr == 1
    ensures false
{
    let q = unsafe { p.add(usize::MAX) };
    assert(q@.addr <= usize::MAX);
    assert(false);
}
```

Its fresh log says “verification results:: 97 verified, 0 errors”. The input condition is satisfiable; the trusted call promises an address of `usize::MAX + 1`, contradicting the pointer address type. The declaration also lacks allocation bounds and the signed offset bound. Passing unrelated negative tests does not repair this trusted inconsistency.

## Corrected trusted wrapper

[Corrected model](../vlm4_sbvfix/sbv_full.rs), lines 169–180:

```rust
#[verifier::external_body]
pub fn ptr_add<T>(p: *mut T, i: usize, Tracked(d): Tracked<&Dealloc>) -> (r: *mut T)
    requires
        i * size_of::<T>() <= isize::MAX,
        p@.addr + i * size_of::<T>() <= usize::MAX,
        p@.provenance == d.provenance(),
        d.addr() <= p@.addr,
        p@.addr + i * size_of::<T>() <= d.addr() + d.size(),
    ensures r@.addr == p@.addr + i * size_of::<T>(), r@.provenance == p@.provenance, r@.metadata == p@.metadata,
{
    unsafe { p.add(i) }
}
```

This names a live allocation token, bounds the offset, and excludes address overflow. The previous `usize::MAX` witness fails. A separate [boundary probe](probes/sbv_fixed_boundaries.rs) copies this wrapper exactly. Its [log](probes/sbv_fixed_boundaries.log) says “verification results:: 2 verified, 2 errors”: an interior offset and a representable one-past address verify; moving one byte beyond the allocation fails `p@.addr + i * size_of::<T>() <= d.addr() + d.size()`; `assert(false)` after a valid allocated-pointer call fails. No contradiction found. These probes test the contract, not the skipped Rust body.

## Layout assumptions, preconditions, and claim scope

The full and heap files declare `global size_of isize == 8;`, `global layout usize is size == 8, align == 8;`, and `global layout Header is size == 16, align == 8;`, with `Header { pub len: usize, pub buffer_len: usize }`. The inline file declares `global size_of usize == 8;`. These are explicit target/layout assumptions consistent with the intended 64-bit target; no contradictory layout was found. They do not establish portability to 32-bit targets. Standard vstd axioms, raw-memory APIs, compiler, and solver remain trusted.

No vacuous top-level precondition was found in the accepted corrected or inline models. Constructors have concrete admissible inputs. Inline `new` establishes the representation invariant; `header_new` constructs initialized permissions under `requires len <= cap, cap <= 64 * 1000000, cap >= 1`. Full-model operations use nonempty bounds, including `cap <= 64_000_000` and, for `push`, `old(self).cap() <= 32_000_000`. These restrictions exclude larger inputs; they do not make all executions impossible. The impossible recursive lemma branch `k >= 64` under “all bits clear” and `d != 0` is a normal contradiction branch, not a vacuous API.

The [inline report](../vlm_servo/smallbitvec/REPORT.md) correctly says “Result: PARTIAL. Inline (tagged-word) half proved; heap half not attempted” and “`get`/`set`/`push` on the *whole* type vs the Seq model therefore NOT proved; only the inline variant is.” Its specifications match that scope.

The [fix report](../vlm4_sbvfix/REPORT.md) correctly qualifies: “still a bounded rewritten model, not upstream smallbitvec”. Its claim “the counterexample no longer verifies; the full proof re-verifies unchanged in scope (96 verified, 0 errors)” matches reruns. Earlier completeness claims remain overstated: the [prior review](../cx_servo/SMALLBITVEC_REVIEW.md) quotes the summary “smallbitvec is now fully proved, inline and heap halves together” alongside the component report's “Not ported” list, including “`resize`, `insert`, `remove`, `extend`, iterators” and “`impl Drop` itself (explicit `free` instead; no drop-glue reasoning)”. Correct pointer arithmetic does not establish these omitted operations or equivalence between exact raw allocation and upstream `Vec` allocation/reallocation.

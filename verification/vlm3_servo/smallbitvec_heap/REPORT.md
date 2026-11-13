# smallbitvec 2.5.3 heap half: Verus with vstd raw pointers
(authored by agents unless marked 🧑)

Upstream: smallbitvec 2.5.3, `src_upstream/smallbitvec-2.5.3/src/lib.rs` (copied from round 1). Verus 0.2026.11.02.
Result: PARTIAL, but the round-1 blocker is lifted. vstd's raw-pointer support is enough to verify the tagged-pointer heap code for allocate, read, write, and free. `reallocate`/`clone`/`push` heap spill are not done.

Rerun: `cd /hdd1/sichangheagent/vl_meeting_work/out/vlm3_servo/smallbitvec_heap && timeout 300 /hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus heap.rs`
Final: `20 verified, 0 errors` (heap.rs, 307 lines; about 195 spec/proof, about 110 exec). Round-1 inline half is in `../../vlm_servo/smallbitvec/sbv.rs` (not merged with this file).
Sanity (mutants fail as they should): `neg1.rs` (dealloc size 8*(1+bl)) -> `precondition not satisfied ... raw_ptr.rs:957 deallocate`; `neg2.rs` (write old word instead of new) -> `assertion failed ... h@[j] == oldh@.update(n, val)[j]`.

## Model
`HeapPerm` (tracked struct) = `PointsTo<Header>` + `Map<int, PointsTo<usize>>` (one permission per buffer word) + `IsExposed` + `Dealloc`. `wf()` says: header init, 8-aligned, `len <= 64*buffer_len`, words at `base+16+8i`, all same provenance, Dealloc matches `(base, 8*(2+buffer_len), align 8)`. `view(): Seq<bool>` with bit i = `(buf[i/64] >> (i%64)) & 1`.
Functions are free functions over `(data: usize, h: HeapPerm)`, not methods on a struct carrying `Tracked<Option<HeapPerm>>` (modelling choice, not tried).

## Proved
- `header_new` (Header::new): result `wf`, `len` as given, `buffer_len*64 >= cap`, first `len` bits all equal `val`.
- `header_raw`: `(data & !1) as *mut Header` equals the header pointer, given `data == base | 1` (tag round trip, via bit_vector, `base % 8 == 0`).
- `get_heap` == `view[n]`; `set_heap` == `view.update(n, val)`, `wf` and `len` preserved (both set and clear branches, bit lemma `bit_set`).
- `drop_heap`: merges header + every word permission back into one `PointsToRaw` and calls `deallocate` with a size matching the allocation (loop invariant over the permission map).
- Also overflow-freedom of `cap + 63`, `8*(2+bl)`, and pointer offsets under the stated bounds.

## What works in vstd (facts, tested)
- `p as usize` for `*mut T` works. `usize as *mut T` does NOT: `Verus does not currently support this cast: usize to *mut Header`.
- Round trip: `let Tracked(exp) = expose_provenance(p); ... with_exposed_provenance(addr, Tracked(exp))` returns a pointer that vstd proves `== p` when addr matches. `IsExposed` is Copy-usable (`Tracked(h.exp)` from a shared ref compiled).
- `allocate(size, align)` returns `(ptr, Tracked<PointsToRaw>, Tracked<Dealloc>)`; requires `valid_layout(size, align)` and `size != 0`. `PointsToRaw::split(set_int_range(a,b))`, `.into_typed::<V>(addr)`, `ptr_mut_write`, `ptr_ref`, `leak_contents` + `into_raw` + `join`, `deallocate` all usable.
- `global layout Header is size == 16, align == 8;` and `global layout usize is size == 8, align == 8;` needed (the `size_of usize` form conflicts with it: `E0428 VERUS_layout_of_usize defined multiple times`).
- `Set::new(|i| ..)` returns `Option<Set>` in this vstd; use `vstd::set_lib::set_int_range` (importing both `set_lib::*` and `iset_lib::*` is ambiguous; `raw.split` wants `Set<int>`, not `ISet`).

## Unsupported / trusted
- Not supported (each: `... is not supported (note: you may be able to add a Verus specification ... assume_specification)`): `Vec::as_ptr`, `mem::forget`, `Vec::from_raw_parts`, `slice::from_raw_parts_mut`, `mem::replace`, `<*mut T>::add`. Tested in `u1.rs`.
- Only `<*mut T>::add` was worked around, with my own trusted `assume_specification` (addr += i*size_of, same provenance); this is the one trusted axiom in the file (`grep assume` = 1 hit).
- Vec-based allocation replaced by `allocate`/`deallocate` plus per-word writes; upstream's `Vec::capacity()` is assumed `== alloc_len` (it uses `capacity()` as `buffer_len` and later frees with `alloc_len == capacity`; if capacity were larger, buffer_len would cover uninitialized memory). Belief: true in practice for `vec![x; n]`, not guaranteed by the Vec contract. Not verified, not a found bug.
- `slice`/`Box<[usize]>` views of the buffer (`buffer_raw`, `into_boxed_slice`-style `InternalStorage::Spilled`) replaced by word-pointer arithmetic. No `PointsTo<[T]>` attempt.
- `reallocate` (Vec::resize/shrink_to_fit) not ported; would need allocate+copy+deallocate (no vstd realloc seen). Not attempted, so `push` spill and `reserve` remain open.
- Header slots: upstream fills them with `init` before overwriting; I only write the buffer words.
- `base != 0` is not provable from `allocate`'s postcondition; dropped from `wf` (not needed).

## Failed attempts (verbatim, trimmed)
1. `error: expected `==`` at `global layout usize is size 8, align 8;` -> syntax is `size == 8, align == 8`.
2. `Verus does not currently support this cast: usize to *mut Header` -> use `with_exposed_provenance`.
3. `no implementation for Tracked<IsExposed> | usize` (I used `expose_provenance(p)` as the address) -> it returns the token; address comes from `p as usize`.
4. `error: `bit_vector` assertion not satisfied` for the tag round trip -> `requires` lacked `data == (a | 1usize)`.
5. `expected Set<int>, found ISet<int>` / `expected Set<_>, found Option<Set<_>>` -> `set_lib::set_int_range`.
6. `precondition not satisfied` at `allocate(8 * n, 8)` -> needs `valid_layout`; `assertion failed` on `is_pow2(8)` until `reveal_with_fuel(is_pow2, 5)`; lemma `valid_8n`. (Message names only the call, not which conjunct.)
7. `cannot call function ptr_mut_write with mode exec` inside `proof {}` -> move exec calls out.
8. `core::ptr::mut_ptr::impl&%0::add is not supported` -> trusted assume_specification.
9. `precondition not satisfied ... into_typed` -> needed `global layout usize` (align) and explicit `(base+16+8*i) % 8 == 0`.
10. `postcondition not satisfied ... r.1@.wf()` for header_new: opaque; fixed by asserting each conjunct of `wf` (found `base != 0` unprovable).
11. `E0133 call to unsafe function add` after verifying -> wrap in `unsafe {}`.
12. `to dereference a mutable reference parameter in a postcondition, disambiguate by wrapping it in either old or final` -> `final(h)`.
Verify iterations: ~25. Wall-clock: ~70 min.

## Takeaways
- Tagged pointers and permission-carrying raw memory are verifiable today; cost is a ghost permission structure (about 40 lines) plus per-op plumbing, not the logic.
- The real gaps are the std shims (`Vec` raw parts, `forget`, `slice::from_raw_parts_mut`, `replace`, `add`), which need either `assume_specification` (trusted) or rewriting to `allocate`.
- No bug found in the heap half under the Vec-capacity assumption.

---
# Round 3b: unified SmallBitVec (inline + heap + spill), `sbv_full.rs`

Rerun: `cd /hdd1/sichangheagent/vl_meeting_work/out/vlm3_servo/smallbitvec_heap && timeout 300 /hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus --crate-type=lib sbv_full.rs`
Final: `96 verified, 0 errors` (982 lines: round-1 inline proof (46 items) + heap.rs functions + new code). One trusted item: the `<*mut T>::add` assume_specification (`grep assume` = 1).

## Type and model
`SmallBitVec { data: usize, perm: Tracked<Option<HeapPerm>> }`. `wf()`: heap case (`data & 1 == 1`) = `perm` is `Some(h)`, `h.wf()`, `data == h.base() | 1`; inline case = `perm` is `None`, `inline_valid(data)`. `view(): Seq<bool>` = `h@` or `iview(data)`. `cap()` = `64*buffer_len` or 62. The round-1 struct is kept as `Inl` (renamed) and called on a temporary `Inl { data }`. `Tracked<Option<_>>` update pattern that works: `let tracked mut h = self.perm.borrow_mut().tracked_take(); f(Tracked(&mut h)); proof { *self.perm.borrow_mut() = Some(h); }`.

## Proved (all against the `Seq<bool>` model, `wf` preserved)
- `new`, `len`, `capacity`, `get_unchecked` == `view[n]`, `set_unchecked` == `view.update`, dispatching inline/heap.
- `set_len`: new len exact, prefix preserved, cap unchanged (new tail elements unspecified, like upstream).
- `with_capacity`: empty view, `cap >= cap` (inline if <= 62, else `header_new`).
- `reallocate`: view unchanged, `cap() >= cap`. Heap branch = allocate + `copy_words` + `drop_heap` (replaces `Vec::from_raw_parts/resize/shrink_to_fit`); inline branch = the upstream algorithm (`with_capacity`, `set_len`, copy loop of `get_unchecked`/`set_unchecked`), which is the inline->heap spill. `*self = new` replaces `mem::replace`.
- `reserve`: view unchanged, `cap >= len + additional`. Uses `checked_add(..).expect(..)` and `saturating_mul` as upstream (both accepted by vstd specs).
- `push` == `view.push(val)`, including the spill when len is 62 and the doubling growth. `pop` == `last`/`drop_last`. `truncate` == `take(len)` (or unchanged). `clear` == empty.
- `clone`: view equal (heap branch allocates same buffer_len, copies header len and all words). `free(self)` (stand-in for `impl Drop`) deallocates with matching size.
- Mutant check: copying 0 words in `reallocate` fails (`assertion failed ... np.bit(i) == old.bit(i)`).

## Bounds added (limits of the proof, not upstream behaviour)
Heap capacity limited to buffer_len <= 1,000,000 words (64M bits); `reserve` needs `cap <= 32M` and `additional <= 32M`; `push` needs `cap <= 32M`; so doubling never exceeds the bound. Larger vectors and the real `capacity overflow` panic path are not covered. Also `size_of usize == 8` is assumed.

## Not ported
`resize`, `insert`, `remove`, `extend`, iterators, `Index`, `Debug`, `Eq/Hash`, bit-wise ops, `into_storage`/`from_storage`/`heap_ptr`, `shrink_to_fit`; `impl Drop` itself (explicit `free` instead; no drop-glue reasoning); no check that callers cannot leak the tracked permission (a leak is just memory, not unsoundness).

## New failures this round (verbatim, trimmed)
1. `error[E0425]/E0422: cannot find type Inl` -> my assembly script dropped the round-1 `impl`; re-appended.
2. `error: in pub open spec function, cannot refer to private function` (`inline_valid`, `iview`, `iget`) -> made round-1 spec fns `pub open`.
3. `E0308 expected nat, found int` for `64 * bl` -> `cap()` returns `int`.
4. `postcondition not satisfied ... final(self).cap() == old(self).cap()` in `set_unchecked` -> `set_heap` also had to ensure `bl()` unchanged.
5. `postcondition not satisfied ... final(self).wf()` and `assertion failed ... self@ =~= ov` in `reallocate` heap branch -> needed explicit `ndata & 1 == 1`, `np.base() == a`, `self.perm@ == Some(np)`, and `header_new` ensures `bl() == (cap+63)/64`.
6. `precondition not satisfied ... len <= old(self).cap()` at `set_len` (push/pop/truncate/clear) and `possible arithmetic underflow/overflow` at `idx + 1`, plus `precondition not satisfied ... std_specs/option.rs:195` for `expect` -> lemma `lemma_len_cap` (`wf ==> len <= cap <= 64M`).
Verify iterations this round: ~9. Wall-clock: ~50 min.

## Takeaway
With vstd permissions, the full Seq-model proof across inline<->heap transitions is feasible and cheap once the word-level primitives (`read_word`, `write_word`, `copy_words`, `set_len_heap`, `drop_heap`) exist; each method then verifies in 1-2 iterations. Remaining cost is porting breadth, not new technique. No bug found.

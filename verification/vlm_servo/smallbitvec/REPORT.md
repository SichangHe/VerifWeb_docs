# smallbitvec — Verus feasibility
(authored by agents unless marked 🧑)

Component: `smallbitvec` 2.5.3 (crates.io tarball, `src_upstream/smallbitvec-2.5.3/src/lib.rs`, 1052 lines).
Result: PARTIAL. Inline (tagged-word) half proved; heap half not attempted (blocked, see below).

Rerun: `cd /hdd1/sichangheagent/vl_meeting_work/out/vlm_servo/smallbitvec && timeout 300 /hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus --crate-type=lib sbv.rs`
Final: `46 verified, 0 errors`. (`--crate-type=lib` is required, otherwise rustc reports `E0601 main function not found`.)

## Proved (file `sbv.rs`, 293 lines)
Model: `view(): Seq<bool>`; inline word encodes element i at bit 63-i, sentinel = lowest set bit, bit 0 = tag 0. Invariant `inv` = bit0==0 && data!=0.
- `new`, `len` (via `trailing_zeros`): view matches, `len <= 62`.
- `inline_shift/inline_index/inline_ones/inline_bits/inline_capacity`: no underflow/overflow in `63 - n`, `1 << shift` (needs `n <= 62`; `inline_index` result nonzero).
- `get_inline` == `view[n]` (the inline branch of `get_unchecked`).
- `set_inline` == `view.update(n, val)`, invariant kept (inline branch of `set_unchecked`).
- `set_len_inline` (verbatim body incl. `!(sentinel - 1)`): new len exact, old elements preserved, no overflow.
- `push_inline` == `view.push(val)` (requires len < 62); `pop_inline` == `last` / `drop_last`.
All arithmetic checked by Verus for overflow (default), so index/bit-math no-overflow holds for the proved functions under stated preconditions.

## Code changes vs upstream
- `data: usize` kept, but `global size_of usize == 8` assumed; `size_of::<usize>()*8` replaced by constant 64.
- `const_debug_assert_le!` in `inline_shift` replaced by a `requires n <= 62`.
- `trailing_zeros()` (not in vstd) replaced by a proved loop (`trailing_zeros` fn).
- Inline branches split out as separate fns (`get_inline`, `set_inline`, `set_len_inline`, `push_inline`) because the heap branch is not modeled; `push` heap spill / `reserve` / `reallocate` omitted.
- `1 << offset` in heap code not ported.

## Blocked / unsupported
- Heap half: `data` is `ptr as usize | 1`; header via `*mut Header`, `Vec::from_raw_parts`, `slice::from_raw_parts_mut`, `mem::forget`, `replace`. Needs ptr<->usize casts with provenance plus raw-memory permission reasoning (vstd `PPtr`/`raw_ptr` possible but a substantial rewrite). Not attempted in the time spent; this is a belief about cost, not measured.
- `get`/`set`/`push` on the *whole* type vs the Seq model therefore NOT proved; only the inline variant is.
- `bit_vector` mode: no `forall`, no struct field access (`self.data` must be bound to a local), spec `-` is `int` so `!(x - 1)` needs `((x-1) as usize)`.

## Failed attempts (Verus output, trimmed)
1. First run: `error[E0601]: main function not found in crate sbv` -> added `--crate-type=lib`.
2. `error: expected finite-width integer in bit_vector proof, got Boxed(Int(Nat))` (my `forall|j: nat|` inside `by (bit_vector)`) -> replaced by inductive lemma `clear_below` + `all_clear_zero`, indices changed to `usize`.
3. `assertion failed ... assert(((d >> (k-1) as usize) & 1) == 0)` and `requires not satisfied ... ((d >> 63usize) & 1) == 0`: my spec `bit` was `== 1` form, so `!bit` didn't give `==0`; the error names the line but not why. Changed `bit` to `!= 0`.
4. `postcondition not satisfied ... ensures r.inv()` for `new`: missing `x != 0`; message only names the whole `inv()`, not the failing conjunct.
5. `Verus does not currently support this expression in bit_vector proofs: UnaryOpr(Field(...data...))` -> bind field to local.
6. `cannot apply unary operator ! to type int` -> cast `((1<<s)-1) as usize`.
7. `to dereference a mutable reference parameter in a postcondition, disambiguate by wrapping it in either old or final` -> `final(self)`.
8. `precondition not satisfied: requires n <= 62` at `inline_index(n)` -> needed lemma `ilen_le` (inv implies len <= 62).
9. `possible arithmetic underflow/overflow` at `!(sentinel - 1)` in `set_len`: real finding, the proof needs `sentinel != 0`; added `r != 0` to `inline_index` (true: sentinel is `1 << (63-len)`, len<=62).
Verify iterations: ~12. Wall-clock: ~35 min. Spec/proof lines ~190 vs ~60 lines of ported code.

## Findings
- No bug found in the inline branch. Upstream `set_len` is only safe because `inline_index(len)` is nonzero (`len <= 62`); upstream guards it with `debug_assert` only (release builds: `unsafe fn` precondition, unchecked).
- Encoding proofs cost mostly bit-lemma plumbing, not logic.

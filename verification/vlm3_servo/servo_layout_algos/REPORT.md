# servo_layout_algos (round 3, bite-sized first pass)
(authored by agents unless marked 🧑)
Upstream: servo/servo @ d275164b2bf624ee5844b22522d10c81b8f606ab (sparse: components/layout); app_units 0.7.8 for Au semantics.
Files: `sizing.rs` (verify: `timeout 300 /hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus sizing.rs`) -> 16 verified, 0 errors.

## Ported (from components/layout/sizing.rs, style_ext.rs)
ContentSizes::{max, union, shrink_to_fit}, SizeConstraint::{new, definite_or_min}, Clamp for Au::{clamp_below_max, clamp_between_extremums}, Au::{add (saturating), min, max}.

## Proved
- Au saturating add stays in [-(2^30-1), 2^30-1]; no i32 overflow.
- shrink_to_fit: result >= min_content always; <= max_content if min<=max; equals available if in [min,max]; malformed (min>max) => exactly min_content (confirms the source comment).
- clamp_between_extremums: >= min; <= max when min<=max; malformed => min; identity when already in range. SizeConstraint::new Definite value obeys the same.
- ContentSizes::max preserves ordering (min<=max); union preserves ordering only for non-negative sizes.

## Failures (verbatim)
1. `error: possible arithmetic underflow/overflow` at `pub const MAX_AU: i32 = (1i32 << 30) - 1;` and `self.0 + o.0` in Au::add. Fix: literal constants (Verus does not const-evaluate the shift expr; then add checks pass).
2. `error: postcondition not satisfied ... self.ordered() && other.ordered() ==> r.ordered()` on ContentSizes::union. Cause: Au can be negative; max(min1,min2) can exceed the sum of maxes (e.g. self=(-5,-5), other=(0,0) -> (0,-5)). Fix: added precondition-style guard max_content >= 0. Not a real Servo bug (sizes are non-negative in practice), but the type does not enforce it.

## Changes to original
Au modelled as struct over i32 with wf spec (no app_units crate); map_or_else closure replaced by match; max_assign/union_assign/Add trait impls not ported (trivial wrappers); `map(f)` with closure not ported.

## Not reached
table/layout.rs column distribution, flexbox free-space, float.rs band math: not attempted (time). OnceCell-based LazySize is likely unsupported (interior mutability).
Effort: ~15 min, 3 verify runs, ~90 lines (about 35 spec/ensures).

# Part 2 (coordinator follow-up): flexbox, float, table
All files verify; rerun: `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus FILE.rs`.
Results: sizing.rs 16/0, flex_cross.rs 14/0, float_fits.rs 9/0, float_fits_rule7.rs 9/0, table_flex_loops.rs 12/0 (verified/errors). `neg/float_fits_rule7_FAILS.rs` is the intentional failing variant.

## flex_cross.rs: flexbox/layout.rs align-content (allocate_free_cross_space_for_flex_line L1051, fallback L760-797, per-line loop L821-833)
Proved:
- Every division in `allocate_free_cross_space_for_flex_line` has a positive divisor given its caller preconditions (`n>=1` for stretch/space-around; space-between guarded by `n>1`).
- `resolve_align` (fallback) only returns SpaceAround/SpaceBetween/SpaceEvenly when `num_lines>=2 && free>0`, and Stretch when `num_lines>=1 && free>0`. So the unguarded `remaining_free_cross_space / num_lines as i32 / 2` (L812) and `/ (num_lines+1)` (L813) can never divide by zero. Result: no div-by-zero panic.
- Per-line loop for Stretch and SpaceBetween with free>0: `rem` stays >= 0 and ends exactly 0, i.e. the source comment "avoid having leftover space ... precision of app units" is true.
Not true (not claimed): SpaceAround / SpaceEvenly do not end at 0 (half-gaps at the container ends are by design).
Failures hit (verbatim essentials):
- `error: in pub open spec function, cannot refer to private const item` -> made consts `pub`.
- `error: postcondition not satisfied ... r == Align::SpaceAround ==> num_lines >= 2 && free.0 > 0` (all four post-conditions, with a correct function). Cause: exec `==` on a plain `#[derive(PartialEq)]` enum carries no spec info. Fix: `match` in exec code and `is Variant` in specs. Verus gave no hint about this; found by elimination.
- `error: invariant not satisfied at end of loop body ... rem.0 >= 0`: needed `div` post-condition `0 <= r <= self` for nonneg self; and exact allocation values in callee ensures.
- `error: invariant not satisfied ... a is SpaceBetween && index + 1 >= num_lines ==> rem.0 == 0`: needed `assert(x/1 == x) by (nonlinear_arith)`.
- `error: assertion failed assert(k == num_lines - index)` (usize->i32 cast): needed `num_lines < 1000000` restated in the loop invariant.
- Spec `/` on `int` is Euclidean, so `r.0 == self.0 / d` fails for negative self; restricted post-condition to `self.0 >= 0`. Source `Au / i32` is truncating; the negative-free-space case (STRETCH never reaches it after fallback) is thus unmodelled.
Changes: AlignFlags -> enum of used variants; Au -> struct over i32 with saturating add/sub, `Div<i32>` truncating.

## float_fits.rs / float_fits_rule7.rs: flow/float.rs FloatBand::object_fits (L570-627)
Proved (exact integers, given nonnegative object size): "fits" for an inline-start object with an inline-end float present implies `candidate_start + size <= inline_end` (no overlap); symmetric for inline-end objects. This is the main collision rule (rule 3).
Failure 1 (verbatim): `error: postcondition not satisfied ... self.inline_end.is_some() ==> ... + size.0 <= self.inline_end.unwrap().0`. Cause: negative `size` equal to MIN_AU makes the saturating `inline_end - candidate` round up. Fixed by `size.0 >= 0` (Au does not enforce this).
Failure 2 (kept as `neg/float_fits_rule7_FAILS.rs`): `error: postcondition not satisfied ... + size.0 <= walls.inline_end.0` for rule 7 (not sticking out past the inline-end wall). Cause: `candidate_inline_start + object.size.inline > walls.inline_end` uses saturating `+`; if the true sum exceeds MAX_AU and `walls.inline_end == MAX_AU`, the sum saturates to MAX_AU, `>` is false, and an object that overflows the wall is reported as fitting. Verifies when `walls.inline_end < MAX_AU`. Assessment: latent, not a practical bug (needs a containing-block end at 2^30-1 Au); this is a claim from the model, not reproduced in Servo.

## table_flex_loops.rs
(A) table/layout.rs `distribute_width_to_columns::blend` (L842-880), integer skeleton, float step abstracted as arbitrary `raw[i]` in [0,MAX_AU]. Proved: after the clamping loop plus the "adjust first column" fix, widths are all >= 0 and sum exactly to `target` (the source's final `debug_assert!(widths.iter().sum() == target_inline_size)`), `remaining` never underflows, and `widths[0] += remaining` cannot saturate. The source's debug_assert that deviation <= len is not needed for this. Does NOT cover that the float computation yields raw values >= 0 or that the weights are valid.
 Failures: `could not automatically infer triggers for this quantifier` (add `#[trigger]`); `postcondition not satisfied` for a lemma sum_set0 (needed `reveal_with_fuel(sum_to, 2)` and a frame assert); `assertion failed 0 <= raw@[i as int]` (restate the forall in the loop invariant); `invariant not satisfied` for `widths[j] <= target` (dropped; replaced by `widths[0] + remaining <= target`).
(B) flexbox/layout.rs `resolve_flexible_lengths` steps 5d/5e (L1415-1461): total_violation is a saturating sum of (clamped-unclamped). Proved: if total != 0, at least one previously unfrozen item becomes frozen, and frozen items stay frozen. So `frozen_count` strictly increases on every non-returning iteration and the `loop` terminates after <= items.len() iterations. Saturation cannot flip the sign of the total (the sum of non-positive terms stays non-positive).
 Failures: `to dereference a mutable reference parameter in a postcondition, disambiguate by wrapping it in either old or final` (Verus 0.2026 new &mut syntax: use `final(x)`); `if and else have incompatible types` (int vs i32 in spec).
Not covered in (B): termination relies on the float path (`scale_by`) not producing NaN; flex factors are f32.

## Not attempted / blocked
- `distribute_extra_width_to_columns` (L946) and colspan distribution: not reached.
- `FloatBandTree` (persistent AA tree on Arc): recursion over Arc<Node> with Option links; not attempted, likely needs `Arc`-in-spec modelling.
- `LazySize` (OnceCell), closures with `FnOnce`: unsupported/unmodelled.
Effort for part 2: ~50 min, ~25 verify runs, 4 files ~400 lines (~45% spec/proof).
Lessons: use `--multiple-errors 10`; exec `==` on enums needs match; `final()` for &mut in ensures.

# Part 3: extra-width/colspan, FloatBandTree, rule-7 reachability
Files (all verify, 0 errors): `float_tree.rs` 12 verified; `table_extra_width.rs` 5 verified. Rerun: `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus FILE.rs`.

## float_tree.rs: FloatBandTree (flow/float.rs L640-880), spec-level
Model: `enum Tree {Leaf, Node(Box<Tree>, key, level, Box<Tree>)}` with key = `band.top` as `int`; skew, split, insert, find, find_next transcribed as spec fns (the AA rebalance shapes match the ASCII diagrams in the source); persistent Arc sharing ignored (semantically invisible).
Proved (induction, ~100 lines):
- skew and split preserve the BST property and the key set.
- insert preserves BST and gives `keys' = keys U {b}` (replace-on-equal case included).
- find returns the greatest key <= x, find_next the least key > x, and `None` exactly when no such key exists.
- With the two sentinels MIN_AU and MAX_AU inserted (FloatContext::new), find(x) is Some for x >= MIN_AU and find_next(x) is Some for x < MAX_AU, i.e. the `.unwrap()`s in `PlacementAmongFloats::new` (L104, L111) cannot panic on a well-formed context.
NOT proved: AA balance invariants (level/height bounds), so no O(log n) claim; `set_range` (the "at least new_value" update over a range, with its pruning conditions `range.start < new_band.top`) not modelled; payload bands not modelled; this is not an exec proof of the Rust (Arc/Option links not ported).
Failures (verbatim essentials): `error: postcondition not satisfied ... ensures bst(skew(t)), keys(skew(t)) =~= keys(t)` plus `assertion failed ... keys(s) =~= keys(t)`. Cause: recursive spec fns unfold only once by default; needed `reveal_with_fuel(keys, 4); reveal_with_fuel(bst, 4)`. Then `assertion failed ... forall x in keys(lr) ==> x < k`: needed `assert forall ... implies ... by { assert(keys(*l).contains(x)); }` (membership facts are not found by the solver on its own). `find_ok` postcondition failed until I explicitly asserted the decomposition of `keys(t).contains(y)` into left / root / right. Final `sentinels_ok` assertion `find(t, x) is Some` failed until I asserted `keys(t).contains(lo)` and `contains(hi)`. Verus errors point at the assertion but never say which membership/unfolding fact is missing.

## table_extra_width.rs: distribute_extra_width_to_columns (L946-1066) and colspan (L582-)
Model: rule-selection chain only (float scale_by abstracted), one loop in place of the iterator filters.
Proved: for rules 1 and 3 the proportional divisor (sum of max-content of the selected set, saturating) is nonzero exactly when a selected column exists with nonzero max-content (so no division by zero / NaN in `max_content / total`); rules 2 and 5 have count > 0; rule 4 has some percent column; rule 6 (equal split over all columns) needs `columns.len() >= 1`, which the caller guarantees by returning early on empty columns; the chain is exhaustive (rule 6 is a catch-all). For colspan: `column_count - percent_columns_count` cannot underflow (guarded by `column_count > percent_columns_count`).
Assumed (not proved): max_content >= 0 for all columns (Au is signed; true in practice); `colspan_cell_constraints.span >= 1` (else `span - 1` underflows as usize: not checked, comes from HTML parsing / table builder, unread).
Not proved: that the distributed increases sum to the excess. Source reading (claim, not machine-checked): unlike the `blend` path, `distribute_extra_width_to_columns` has no remainder fix-up after `scale_by` rounding, so the column sum can differ from `assignable_width` by up to about one Au per column (1/60 px). I did not check whether any caller tolerates this.
Failures: none beyond the earlier-lesson ones (first attempt verified).

## Rule-7 reachability (walls.inline_end == MAX_AU), source reading only; nothing executed
`walls` is `FloatContext.containing_block_info`. Its `inline_end` is set by (a) `FloatContext::new(max_inline_size)` L353 via `SequentialLayoutState::new(containing_block.size.inline)` (flow/mod.rs:460) and (b) `same_formatting_context_block.rs:272`: `inline_end: inline_start + containing_block_for_children.size.inline`, a saturating Au add. `Au` values are clamped to MAX_AU = 2^30-1 (about 17.9M CSS px). So an author-supplied huge width (e.g. `width: 100000000px`, which saturates) on a block containing floats makes `inline_end == MAX_AU`. For the wrong answer a second condition is needed: the band already has an inline-start float (`self.inline_start.is_some()`) and `candidate_inline_start + object.size.inline` exceeds MAX_AU, i.e. another enormous float. Verdict: reachable from CSS in principle, only with two absurd (~10^7 px) sizes; no real-page impact; the only code that constructs MAX_AU contexts directly is tests/floats.rs:476 (`FloatContext::new(MAX_AU)`). The consequence would be a float placed past the wall instead of pushed down, in an already-saturated coordinate space where everything else is clamped too. Not reproduced by running Servo.

Effort part 3: ~40 min, ~9 verify runs.

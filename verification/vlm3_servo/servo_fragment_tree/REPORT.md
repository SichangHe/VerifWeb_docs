# servo_fragment_tree (Servo components/layout fragment_tree)
(authored by agents unless marked 🧑)
Upstream: https://github.com/servo/servo @ d275164b2bf624ee5844b22522d10c81b8f606ab (sparse, components/layout) in src_upstream/servo. Au semantics from app_units 0.7.8 (src_upstream/au).
Final file: frag.rs. Rerun: `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus frag.rs` -> 17 verified, 0 errors (one harmless snake-case warning).

## What was ported (status: partial; models, not verbatim)
- Au = i32 saturating to +-(2^30-1) (fact: app_units Add/Sub clamp). `au_add/au_sub` verified to equal clamp(a+b), stay in range, no i32 overflow.
- `Rect::translate`, `max_x`, `outer_rect` (basis of `padding_rect/border_rect/margin_rect`, `BoxFragment::cumulative_*_box_rect`, `offset_by_containing_block`): proved result stays in Au range.
- `ContainingBlockManager::containing_block_for_box` / `new_for_*` (containing_block.rs), with T=u32 and Option<&T> -> Option<u32>: proved selection table (Fixed->abs_fixed; Absolute->abs or fallback abs_fixed; else non_abs) and that new_for_absolute_and_fixed_descendants makes all kinds resolve to the new block.
- Traversal (`Fragment::find`): spec tree `Frag` with `Seq<Frag>` kids; `size`/`size_from` terminate (Verus accepted decreases through Seq element); `abs_origin_x` = clamped running sum of origins along a path (what find's `content_rect.translate(parent.origin)` computes) proved always in Au range.

## Finding (inference-level, not a confirmed bug)
Containment `content_rect subset padding_rect` (outer_rect) does NOT hold unconditionally under saturation. Verus proved the counterexample `outer_not_contain_cex`: x=5, w=MAX_AU, left=10, right=0: new x=-5, new w=clamp(MAX+10)=MAX, so new max_x = MAX-5 < old max_x = MAX. Holds when w+left+right <= MAX_AU (proved, `outer_contains_x`). Only reachable with ~16M px sizes; likely benign.

## Failures (verbatim)
1. First size_seq attempt (decreases on (k, n), recursing into k[n-1]):
```
error: could not prove termination
73 |     if n <= 0 { 0 } else { size_seq(k, n - 1) + size(k[n-1]) }
note: recommendation not met   (seq.rs:980:12)
```
Fix: decreases f, 1 / f, 0, idx on the enum itself; recurse on kids[i] (vstd's seq-index decreases axiom then applies).
2. Unconditional containment: `error: postcondition not satisfied ... failed this postcondition` (the ensures x2<=x && max'>=max). Message gives no counterexample; I found it by hand, then confirmed via assert. Fix: add precondition w+l+r<=MAX.

## Blockers (not attempted / cannot verify directly)
- `Arc<BoxFragment>`, `Fragment` enum holding Arc (Box/Float/LayoutRoot): exec Arc<T> with interior mutation unsupported; tree must be modeled as value datatype (done in spec only). An exec recursive traversal over `Vec<Fragment>` was not attempted.
- `BaseFragment.rect: SyncPhysicalRectAu` (AtomicI32s), `status: AtomicU8`, `scrollable_overflow_is_up_to_date: AtomicBool` with Acquire/Release, `Cell<Option<..>>`: atomics need vstd atomic ghost-perm API; Cell needs PCell. Caching correctness (scrollable_overflow memo) therefore untouched.
- `ArcRefCell`/`AtomicRef` (`rare_data`, `style()`): atomic_refcell not supported; `grid_info()` unmodelable.
- Style dependency: `box_fragment.style()`, `get_box().position`, `establishes_scroll_container`, `effective_overflow`, `overflow_direction`, `calculate_transform_matrix` come from the `style` crate (huge, Gecko-derived, ServoArc); I replaced `Position` with a local enum. `scrollable_overflow_for_parent`, `clip_wholly_unreachable_scrollable_overflow` (euclid Box2D intersection, is_negative) and transforms (f32 matrix) not ported; f32 rect transform is the hardest.
- euclid generics `Rect<Au, U>`, `Vector2D`, `Add` trait impls on Au: ported by hand to i32 functions; no trait-generic verification.
- `process_func: impl FnMut` in `find`: closures with FnMut and early exit via find_map need Verus closure specs; only the pure path-sum was modeled.

## Effort
~25 min, 4 verify runs, ~110 lines of which ~60 spec/proof. Next steps: exec recursive `find` over a Vec-based tree with ghost path sum; port `scrollable_overflow` union fold; model BoxFragment sides with non-negativity of rect sizes (union/is_negative).

---
# Round 2 additions

Files (all verify; rerun `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus <file>`):
- `arc.rs`: Arc smoke test. Verus accepted `Arc<B>` with `Arc::new`, `.clone()` (ensures result == *a), field read through `&Arc<B>`, and `Vec<Arc<B>>` children. (Fact: vstd's std_specs model Arc as a transparent pointer to a value; no interior mutability.) The only error was my own missing loop `decreases`. Result: shared immutable children via Arc work.
- `find.rs`: 4 verified, 0 errors. Exec recursive `find` (port of `Fragment::find`, FnMut closure replaced by "absolute x == target" test) over `Node { x: i32, kids: Vec<Arc<Node>> }`.
  - Proved: terminates, absolute origin accumulated with saturating `au_add` (preconditions in Au range), returned level is within [level, level+depth].
  - Termination: Vec<Arc<Node>> gives no structural decreases order, so I use a ghost fuel `d` (tree depth bound) with spec `ok(n, d)`. Real code would need a depth-bound invariant on the whole tree; Servo has none stated, a proof would have to establish one from construction.
  - Verbatim failure, first attempt (`level < 1000000` as precondition): 
```
error: precondition not satisfied
  --> find.rs:36:17
24 |     requires ok(&**n, d@), inr(px as int), level < 1000000,
   |                                            --------------- failed precondition
36 |         let r = find(&n.kids[i], ax, level + 1, ...
```
  It tells which precondition, not why: `level+1` is not bounded by the recursion. Fix: `level + d <= 1000000`. This is a genuine requirement: in Servo `level: usize` could only overflow at absurd depth, so no bug.
- `sov.rs`: 7 verified, 0 errors. Port of `scrollable_overflow_for_parent` minus the transform branch (needs f32 matrix + `style`); style predicates `establishes_scroll_container`, overflow x/y == Visible became bool parameters. Proved: result in Au range; scroll container returns border rect; non-visible axis unchanged; on a visible axis origin <= min(border.y, so.y); and, when no saturation, new bottom >= both bottoms.
  - Verbatim failure, first attempt (precondition only bounded the input bottoms):
```
error: postcondition not satisfied
  --> sov.rs:26:13
   ... failed this postcondition   (o.y+o.h >= border bottom && >= so bottom)
```
  Reason (my analysis): `by - ov.y` is `au_sub` and saturates when max(bottoms) - min(origins) > MAX_AU; e.g. min origin -MAX, bottom MAX gives height MAX, bottom 0 < MAX. Fix: precondition max(bottoms)-min(y) <= MAX_AU. Same class as the `outer_rect` saturation. Unproven outside that condition, so a very tall child + far-negative origin shrinks reported scrollable overflow (inference, extreme values only).

## Is the content_rect saturation case reachable from real callers?
Inference from reading source, not executed:
- `padding_rect/border_rect/margin_rect` (box_fragment.rs:370-380) feed callers in query.rs (734-745, 277, 1632), fragment.rs (262, 327, 331), table/layout.rs (1677, 1733), taffy/mod.rs:224, display_list/clip.rs:98.
- Au sizes clamp rather than wrap: `Au::from_f32_px` -> `from_f64_au` clamps to +-MAX_AU (app_units 0.7.8 app_unit.rs:229), and layout code explicitly produces MAX_AU (replaced.rs:641,646; table/layout.rs:881 comment "huge values whose sum is clamped to MAX_AU").
- So a content box with width clamped to MAX_AU (e.g. author CSS `width: 1e9px`, MAX_AU is ~17.9M px) plus nonzero padding/border and origin x < left+... triggers the counterexample `x=5, w=MAX_AU, left=10`: reported border-box max_x is smaller than the content box's. The reachable effect would be wrong `getBoundingClientRect`/hit-test extents for absurd widths. Not confirmed by running Servo; classified likely-benign, low-severity possible bug.

## Remaining
- Combining `find.rs` with `Rect` origin paths and the `process_func` closure postcondition (Verus FnMut spec) not done.
- `scrollable_overflow` caching with atomics (AtomicBool Acquire/Release) still unattempted; vstd atomics (`PAtomicBool`) would be needed.
- Tree depth invariant for Servo trees is assumed, not proved.

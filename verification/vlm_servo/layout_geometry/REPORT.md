# layout_geometry: app_units 0.7.8 and euclid 0.22.14
(authored by agents unless marked 🧑)

Upstream (crates.io tarballs, in src_upstream/): app_units 0.7.8 (src/app_unit.rs), euclid 0.22.14 (src/box2d.rs, src/rect.rs).
Result: proved (all properties below), with listed code changes.

## Rerun
V=/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus
timeout 300 $V au.rs          # 21 verified, 0 errors
timeout 300 $V box.rs         # 11 verified, 0 errors
timeout 300 $V rect.rs        # 11 verified, 0 errors
(negative runs: au_neg1.rs, rect_nopre.rs fail as shown below)

## Properties proved
au.rs (Au as `struct Au(pub i32)`, MIN_AU=-(2^30-1), MAX_AU=2^30-1, spec clampi):
- clamp/new: result == clampi(input), always in [MIN_AU, MAX_AU]
- add/sub: no i32 overflow and result == clampi(exact sum/diff), given both operands valid (in range)
- mul_i32 (Au*i32): no panic for any Au/i32; result == clampi(exact product) (including the saturation branch with the sign xor); result valid
- from_px(px) == clampi(60*px), for every i32 px
- to_px: truncating division, |result| <= 17895697
- neg, abs on valid values: no overflow, valid result
- lemma roundtrip: for |px| <= 17895697, from_px(px).to_px() == px (no clamping)
box.rs (Box2D<i32>):
- intersection returns Some(s_isect) iff that box is non-empty (functional spec), and a point is in the result iff it is in both inputs (spatial spec)
- commutative: a.intersection(b) == b.intersection(a)
- contained: Some(i) implies a.contains_box(i) and b.contains_box(i)
- union: empty cases return the other box; otherwise every point of either input is in the result
rect.rs (Rect{x,y,w,h} i32, via Box2D as upstream does): non-empty intersection lies inside both inputs' [x, x+w) x [y, y+h); no overflow in max-min.

## Failures (verbatim, trimmed) and what they said
1. First au.rs: `error: `core::num::impl&%2::abs` is not supported ... assume_specification`. Fix: replaced i32::abs by a branch.
2. Consts `Au(-((1 << 30) - 1))`: `error: possible arithmetic underflow/overflow` at 3 spots in const initializers. Fix: literals 1073741823.
3. After 2, `postcondition not satisfied ... clamp` : Verus does not unfold the const MIN_AU.0 (opaque). Fixed by the same literals. Message pointed at the ensures, but not the real cause (cost me a guess).
4. mul_i32 postcondition failed 3 times (only "failed this postcondition ... at the end of the function body", no branch named). Needed: (a) `possible arithmetic underflow/overflow` on the i64 product: add nonlinear_arith bound assertion; (b) sign facts in each saturation branch: assert p < i32::MIN (resp. > i32::MAX) by(nonlinear_arith). A stray assertion I added (`a != 0 && b != 0 || p == 0`) failed: "assertion failed" (it was false for zero inputs without nonlinear help; deleted).
5. box.rs: `cannot call function box::max with mode exec` in ensures: need separate spec fns smax/smin. `cannot call ... contains_box with mode exec` in assert: call it in exec and assert on the bool. `in pub open spec function, cannot refer to private function`: make helpers pub open.
6. Real proof gaps (informative): `assert(r1 == r2)` (commutativity) and `assert(c1 && c2)` failed with plain "assertion failed" when intersection only had a spatial postcondition (set-semantics does not imply struct equality). Fix: add functional ensures `r == if s_empty(s_isect(a,b)) {None} else {Some(s_isect(a,b))}`; then both pass. Lesson: specs must be extensional-equality-strong for Verus.
7. Negative (genuine upstream preconditions), au_neg1.rs (drop valid(other)):
   `error: possible arithmetic underflow/overflow --> au_neg1.rs:25:10 Au(self.0 + other.0).clamp()` and same for sub (line 30).
   So Au::add/sub panic (debug) / wrap (release) on out-of-range Au; this matches the doc: "It is safe to construct invalid Au values, but it may lead to panics and overflows." The validity invariant (pub field) is not type-enforced.
8. rect_nopre.rs (no preconditions on Rect::intersection):
   `possible arithmetic underflow/overflow` at `self.x + self.w` (x2), `other.x + other.w`, `other.y + other.h`. Real: euclid Rect::max_x/to_box2d do unchecked origin+size in T=i32 (e.g. x=i32::MAX, w=1). With Au this cannot happen if all are valid, but Au `+` clamps, so no overflow there.

## Observations (not bugs, my inference)
- Au::neg, Au::abs, Div<Au>/Rem (divide by zero, MIN/-1) have no clamp or checks; I proved neg/abs only for valid input. Div by zero panics by design.
- Au::to_px truncates toward zero (documented); ceil_to_px/to_nearest_px/scale_by use f64 and `as i32`; not verified (Verus float support is minimal).
- `Ord::clamp`, derive(Ord), `checked_mul`, `i32::abs` not usable as-is.

## Code changes to upstream
- Dropped Debug/serde/num_traits/malloc_size_of, operator traits turned into methods (add, sub, neg, mul_i32) to avoid trait/spec plumbing.
- `Ord::clamp(self, MIN_AU, MAX_AU)` -> explicit if/else (derived Ord not supported by Verus here).
- `checked_mul` -> i64 multiply + range test (equivalent semantics).
- MIN_AU/MAX_AU as literals.
- `abs` -> branch. Box2D/Rect: generic T and unit U removed (specialised to i32), Point2D/Size2D inlined as fields, `min`/`max` helper functions re-defined with specs (upstream uses partial-ord helper functions).
- Not ported: float conversions, Rect::union (via Box2D::union is proved on Box2D), Rect::contains etc.

## Effort
~25 min wall-clock, ~14 verify runs. Lines: au.rs 69 total (about 20 spec/proof, rest code), box.rs ~70 (about 30 spec), rect.rs ~85 (spec ~20). Verus was fast (<2s per file). Hardest part: nonlinear i64 multiplication reasoning in mul_i32.

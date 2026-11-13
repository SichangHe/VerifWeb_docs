# Layout and fragment proof audit
(authored by agents unless marked 🧑)

No local trusted assumption or inconsistent axiom was found in the 12 distinct files (24 paths). Ten files verify. `arc.rs` fails before reporting a verified count; the intentional rule-7 negative test reports 8 verified, 1 error. Several reports overstate what their contracts establish. Three new mutation probes verify despite deliberately wrong functional behavior.

“Sound” below means no unsoundness found in the stated model contract; it is not an independent proof of Verus or its standard library. “Overstated” means a report claims more than the checked contract; it does not mean `assert(false)` was derived.

## Scope, trust, and counts

Every relative path below exists beneath **both** `out/vlm3_servo/` and `out/cx_servo/layout_work/`; each pair is byte-identical. Upstream source snapshots are ordinary Rust, not Verus proof files. Baseline reruns were performed by the coordinating audit, recorded in [results.json](results.json); each entry links its file paths to `logs/<sha256>.log`. The command is `tools/verus-x86-linux/verus FILE --multiple-errors 10`.

All rows have **no local trusted items**: no `assume`, `assume_specification`, `external_body`, `admit`, `#[verifier::external]`, or user axiom. `frag.rs` contains the comment “kids[i] < f by vstd seq-element decreases axiom”; it invokes the standard library's sequence termination machinery, not a locally declared axiom. Standard Verus/vstd trust remains, including Arc and collection specifications.

| Relative file | Verified / errors | Verdict |
| --- | --- | --- |
| `servo_fragment_tree/arc.rs` | no count; rejected | overstated |
| `servo_fragment_tree/find.rs` | 4 / 0 | sound, weak search contract |
| `servo_fragment_tree/frag.rs` | 17 / 0 | sound, restricted model |
| `servo_fragment_tree/sov.rs` | 7 / 0 | overstated |
| `servo_layout_algos/sizing.rs` | 16 / 0 | overstated |
| `servo_layout_algos/flex_cross.rs` | 14 / 0 | overstated |
| `servo_layout_algos/float_fits.rs` | 9 / 0 | sound, rule 3 only |
| `servo_layout_algos/float_fits_rule7.rs` | 9 / 0 | sound, restricted boundary |
| `servo_layout_algos/float_tree.rs` | 12 / 0 | overstated |
| `servo_layout_algos/table_extra_width.rs` | 5 / 0 | overstated |
| `servo_layout_algos/table_flex_loops.rs` | 12 / 0 | overstated |
| `servo_layout_algos/neg/float_fits_rule7_FAILS.rs` | 8 / 1 | negative test, rejected |

No globally impossible precondition was found. Concrete admissible families include zero-valued bounded Au/rectangles, zero sides, a leaf with `d=0` and `level=0`, nonempty zero raw-width vectors, empty frozen/delta vectors, a singleton zero-content column, `Leaf` for BST lemmas, and `lo=0, hi=1` for sentinel construction. Flex allocation admits `n=1, free=1, Stretch`; the line loop admits the same. Float checks admit zero walls/size and absent bands, including the strict rule-7 upper bound. These witnesses establish satisfiability, not that Servo callers meet the preconditions.

## Contract and report mismatches

### Fragment files

**`arc.rs`: the reported successful file is rejected.** The fragment [report](../vlm3_servo/servo_fragment_tree/REPORT.md) introduces the additions as “Files (all verify; rerun”. The current baseline log says “error: loop must have a `decreases` clause” for `sum`'s loop. Its Arc construction/read/clone examples are separate from this missing termination measure. Do not count this file as a successful verification.

**`find.rs`: termination and return-depth bounds do not establish search correctness.** Its complete functional postcondition is `r is Some ==> level <= r->Some_0 <= level + d@`. The report accurately limits the claimed result to “returned level is within [level, level+depth]” and explicitly leaves closure postconditions unfinished. There is no theorem connecting a result to the target, first-match order, or completeness. Replacing the whole function body with `{ None }` still verifies: [probe](layout_probes/find_always_none.rs), [log](layout_probes/find_always_none.log), “verification results:: 3 verified, 0 errors”. Preconditions `ok(&**n, d@)` and `level + d@ <= 1000000` restrict the caller; real tree construction is not verified. This probe shows contract weakness, not an error in the supplied algorithm.

**`frag.rs`: the stated restricted numeric and containing-block results are sound on inspection.** `outer_contains_x` explicitly requires `r.w as int + s.l as int + s.r as int <= MAXAU()`. Its counterexample theorem addresses saturation outside that restriction. `outer_rect` itself ensures only `rect_ok(o)`; the containment lemma separately concerns arithmetic expressions. Tree size and path-sum functions are specification models, not verification of Servo's executable traversal. No local trust to attack was present.

**`sov.rs`: x-axis claims are unproved.** The fragment report says “non-visible axis unchanged; on a visible axis origin <= min(border.y, so.y); and, when no saturation, new bottom >= both bottoms.” Only y has preservation/containment clauses. Replacing the visible-x update with `ov.x = 0; ov.w = 0;` still verifies: [probe](layout_probes/sov_wrong_x.rs), [log](layout_probes/sov_wrong_x.log), “verification results:: 7 verified, 0 errors”. For a visible x axis and border x=5, width=1, this mutation discards the border extent. The proved y properties also require their written visibility, scroll-container, and saturation guards. Add symmetric x contracts or restrict the report to y.

### Layout files

**`sizing.rs`: `SizeConstraint::new` does not prove all advertised clamp properties.** The layout [report](../vlm3_servo/servo_layout_algos/REPORT.md) states: “clamp_between_extremums: >= min; <= max when min<=max; malformed => min; identity when already in range. SizeConstraint::new Definite value obeys the same.” The Definite contract supplies only well-formedness and lower/conditional upper bounds. It does not supply identity or malformed-input equality. `definite_or_min` has no functional postcondition. The implemented code appears consistent with those stronger properties, but the written contract does not establish them. The report's “union preserves ordering only for non-negative sizes” also describes a sufficient guard as necessary; the contract is an implication, not an equivalence.

**`flex_cross.rs`: positive line count does not establish safety of the source's integer cast.** The report concludes “the unguarded `remaining_free_cross_space / num_lines as i32 / 2` (L812) and `/ (num_lines+1)` (L813) can never divide by zero. Result: no div-by-zero panic.” The model bounds allocation counts with `0 <= n < 1000000` and line-loop counts with `1 <= num_lines < 1000000`; `resolve_align` only establishes positive/lower-bounded `usize` counts. On a 64-bit target `num_lines=2^32` is positive but casts to i32 zero. No proof connects the source count to the model's upper bound. The verified zero-remainder theorem additionally requires positive free space and Stretch or SpaceBetween (at least two lines for SpaceBetween). These conditions are satisfiable, not vacuous.

**`float_fits.rs` and `float_fits_rule7.rs`: sound restricted contracts.** The former ensures nonoverlap only when an opposing float exists and size is nonnegative. The latter adds inline-start rule 7 under `walls.inline_end.0 < MAX_AU`. Neither proves all directions of fitting or all wall boundaries; the component report distinguishes rule 3 and rule 7. No trusted item is involved in the excluded boundary failure.

**`float_tree.rs`: the executable caller safety conclusion exceeds the specification model.** The report says “With the two sentinels MIN_AU and MAX_AU inserted (FloatContext::new), find(x) is Some for x >= MIN_AU and find_next(x) is Some for x < MAX_AU, i.e. the `.unwrap()`s in `PlacementAmongFloats::new` (L104, L111) cannot panic on a well-formed context.” `sentinels_ok` constructs exactly `insert(insert(Leaf, lo), hi)`. Preservation under later inserts can be composed from the other lemmas, but `set_range`, payloads, and actual context construction are unverified. The checked BST/key-set/predecessor/successor lemmas have substantive contracts and no local assumptions; the source-wide unwrap conclusion remains conditional reasoning.

**`table_extra_width.rs`: rule selection is substantially underspecified.** The report claims the proportional divisor is nonzero “exactly when a selected column exists with nonzero max-content”. The postconditions only give one-way selected-member implications. Even replacing `choose_rule` with `{ 6 }` verifies: [probe](layout_probes/choose_always_six.rs), [log](layout_probes/choose_always_six.log), “verification results:: 4 verified, 0 errors”. A nonempty vector always satisfies the entire rule-6 clause, so the contract cannot distinguish this wrong selection from the intended priority chain. `colspan_ratio_guard` never uses its `non_percent_sum` argument and proves no division. No actual percentage or floating-point divisor is modeled. Strengthen the contract to characterize which rule applies, or describe the current one-way guarantees.

**`table_flex_loops.rs`: a progress step is not a verified outer loop.** The report says “So `frozen_count` strictly increases on every non-returning iteration and the `loop` terminates after <= items.len() iterations.” `freeze_step` proves monotonic frozen flags and a newly frozen item when `total != 0`; the outer loop and its return case are absent. The result supports a mathematical termination argument for a loop satisfying these conditions, not direct verification of the original loop. The report also says “Saturation cannot flip the sign of the total (the sum of non-positive terms stays non-positive).” The parenthetical is true; the unrestricted claim is false: for M=1073741823, `[M,M,-M,-1]` sums exactly to M-1 but saturates sequentially to -1. The actual proof only needs an item sharing the saturated sum's sign, so this does not invalidate it. `blend_int` soundly verifies nonnegative output and exact target sum under its explicit nonempty/bounded/nonnegative raw-input assumptions; floating-point production and the removed source deviation assertion remain outside the proof.

## Rejected negative test

`neg/float_fits_rule7_FAILS.rs` removes the strict upper-wall restriction and asserts the stronger rule-7 postcondition. The current rerun gives “verification results:: 8 verified, 1 errors”. A concrete arithmetic witness is `candidate=MAX_AU-1`, `size=2`, `wall=MAX_AU`, an inline-start float present and no opposing float: saturated addition equals the wall, so the algorithm accepts, while the exact right edge exceeds it by one. This is rejection of an invalid property, not an unsound accepted proof.

## Limits

No local trusted items existed to exploit in this assignment, and no contradiction was derived. The three accepted mutations demonstrate missing functional guarantees. They do not show that the original implementations return those wrong results. Upstream reachability, browser rendering effects, and Verus/vstd soundness were not established by this audit.

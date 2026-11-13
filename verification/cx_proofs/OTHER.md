# Bitsets, geometry, Bloom filter, URL, and diagnostic proof audit
(authored by agents unless marked 🧑)

No local trusted assumptions were found in these 16 distinct proof files (18 paths counting duplicates). No contradiction was derived. `au.rs` has an overstated rounding claim; the remaining successful files support their stated, restricted properties. This is an audit conclusion, not a proof of Verus or its standard library's soundness.

## Finding: app-unit rounding claim exceeds the contract

`out/vlm_servo/layout_geometry/REPORT.md`, “Properties proved”, says: “to_px: truncating division, |result| <= 17895697”. But `au.rs:60–64` specifies:

```rust
fn to_px(self) -> (r: i32)
    requires valid(self)
    ensures r == self.0 as int / 60 || (self.0 < 0 && r as int == -((-(self.0 as int)) / 60)),
            -17895697 <= r <= 17895697
{ self.0 / AU_PER_PX }
```

The first disjunct permits mathematical floor division for negative input. The existing probe `probes/models_au_wrong_rounding.rs` changes only the body to `{ if self.0 == -1 { -1 } else { self.0 / AU_PER_PX } }`. Rerunning it produced “verification results:: 21 verified, 0 errors” (`other_logs/au_wrong_rounding.log`). Thus the contract accepts -1 instead of Rust's correct result 0 at input -1. The original implementation is correct; its postcondition does not establish the reported truncation rule. Replace the disjunction with a sign-dependent equality.

The round-trip lemma is an arithmetic lemma, rather than an executable call chain: `ensures clampi(px*60) == px*60, (px*60)/60 == px`. Its arithmetic statement is sound and, with the method contracts, sufficient for the stated restricted round-trip; it does not repair the general rounding contract.

## Other specification limits

`rect.rs:72–78` ends its result contract with `None => true`. Replacing the entire Rect intersection body with `{ None }` still gives “verification results:: 11 verified, 0 errors” (`probes/other_rect_always_none.log`). This proves only containment when a result is returned, not completeness or the exact intersection. The report explicitly limits its claim to “non-empty intersection lies inside both inputs' [x, x+w) x [y, y+h); no overflow in max-min.” Verdict: sound for that stated property. The overflow preconditions admit ordinary rectangles, e.g. x=y=0, w=h=1.

`box.rs` proves exact intersection and the reported union containment property. Its union contract promises containment, not a minimal bounding box, matching the report: “otherwise every point of either input is in the result”. It needs no input precondition.

The bitset port requires `lo <= hi, hi <= 64, lo < 64`. This excludes (64,64) but admits (0,0) and (0,64); it is not vacuous. Its report explicitly says “with one precondition upstream does not state”. The fixed bitset proof includes (64,64) and verifies the empty result; the original release behavior is a mathematical model with explicitly masked shifts, not a machine-checked compiler-semantics theorem.

Bloom `v2.rs` requires `old(self).wf(), old(self).items@.contains(hash)` on removal. These are satisfiable, including an inserted hash with coincident slots. The invariant allows counters equal to 255 independently of occupancy, reflecting permanent saturation. The report accurately qualifies removal safety: “given the remove precondition”. Construction/initialization is outside the proof; the report explicitly lists “Default” and “clear” as dropped. `remove_hash`'s exported postcondition gives invariant preservation and length reduction, while its proof body removes the matching ghost entry. An API theorem identifying exactly which item was removed would need a stronger exported postcondition.

`path_spec.rs` explicitly begins “Verus model: WHATWG URL "path state" (hand-transcribed spec) vs rust-url 2.5.8 parser.rs”. Its implementation is modeled by spec functions, not verified Rust parser execution. Agreement requires `run_ok`, which recursively excludes the explicitly defined divergence cases; it does not assume equality itself. The file also proves five concrete divergences without preconditions. The `parse_path_agree` postcondition applies `s_tail` for files; the comment defines this as “The old-spec "while path size > 1 and path[0] is empty, remove it" (NOT in the current path state).” Thus it is not unrestricted conformance to the current URL standard. Verdict: sound as the labeled conditional model proof.

## Per-file reruns and verdicts

Commands used `/hdd1/sichangheagent/vl_meeting_work/tools/verus-x86-linux/verus FILE --multiple-errors 10`. Full outputs and commands/paths are recorded in `other_logs/` and `other_rerun.json`. Each entry below quotes Verus's verified/error counts. Trusted items: none in every listed file. “Rejected” entries are failed proof attempts/negative controls, not accepted unsound proofs; assigning them a sound/unsound theorem verdict would misrepresent the result.

- `out/cx_bugs/bitset/bitset_from_range.rs`: “verification results:: 13 verified, 0 errors”; trusted items: none; verdict: sound within stated scope.
- `out/vlm3_review/job1/bitset_from_range.rs`: “verification results:: 13 verified, 0 errors”; trusted items: none; verdict: sound within stated scope.
- `out/cx_bugs/bitset/bitset_original_fails.rs`: “verification results:: 13 verified, 1 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/vlm3_review/job1/bitset_original_fails.rs`: “verification results:: 13 verified, 1 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/cx_synth/questions_evidence/conjunction.rs`: “verification results:: 0 verified, 1 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/cx_synth/questions_evidence/expand.rs`: “verification results:: 1 verified, 1 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/cx_synth/questions_evidence/feedback.rs`: “verification results:: 1 verified, 5 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/vlm2_url/verus_path/path_spec.rs`: “verification results:: 32 verified, 0 errors”; trusted items: none; verdict: sound within stated scope.
- `out/vlm_servo/jit_piece/bitset.rs`: “verification results:: 17 verified, 0 errors”; trusted items: none; verdict: sound within stated scope.
- `out/vlm_servo/jit_piece/bitset_v1_fail.rs`: “verification results:: 10 verified, 1 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/vlm_servo/layout_geometry/au.rs`: “verification results:: 21 verified, 0 errors”; trusted items: none; verdict: overstated (rounding claim).
- `out/vlm_servo/layout_geometry/au_neg1.rs`: “verification results:: 19 verified, 2 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/vlm_servo/layout_geometry/box.rs`: “verification results:: 11 verified, 0 errors”; trusted items: none; verdict: sound within stated scope.
- `out/vlm_servo/layout_geometry/rect.rs`: “verification results:: 11 verified, 0 errors”; trusted items: none; verdict: sound within stated scope.
- `out/vlm_servo/layout_geometry/rect_nopre.rs`: “verification results:: 10 verified, 1 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/vlm_servo/selectors_bloom/neg.rs`: “verification results:: 18 verified, 1 errors”; trusted items: none; verdict: rejected; not a verified proof.
- `out/vlm_servo/selectors_bloom/v1.rs`: “verification results:: 11 verified, 0 errors”; trusted items: none; verdict: sound within stated scope.
- `out/vlm_servo/selectors_bloom/v2.rs`: “verification results:: 19 verified, 0 errors”; trusted items: none; verdict: sound within stated scope.

`questions_evidence/config.rs` and `verifier.rs` are copied verifier implementation sources, not standalone Verus proofs. The three small diagnostic proofs intentionally fail: `conjunction.rs` demands `x == x && x > 0` for arbitrary x; `expand.rs` asserts `false && false`; `feedback.rs` contains bad calls, arithmetic, postconditions, and assertions. Their rejection is expected.

The added URL witness `probes/other_url_nonvacuous.rs` proves `wf_segs` and `run_ok` for the one-segment path `x`, then calls `parse_path_agree`. Verus reports “verification results:: 33 verified, 0 errors” (`probes/other_url_nonvacuous.log`), establishing that the main agreement theorem has at least one admissible input. All reruns emit a nonfatal GLIBC weak-version warning; the quoted verification summaries and exit codes are retained.

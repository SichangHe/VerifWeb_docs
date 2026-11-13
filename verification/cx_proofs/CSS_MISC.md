# CSS parser and Servo miscellaneous proof audit
(authored by agents unless marked 🧑)

No inconsistent trusted axiom was found in this subset. The only local trusted item is the negative-number parser stub in `nth_full.rs` and its negative-test variant. Its contract is consistent but insufficient for parsing semantics. Several published statements exceed the proved model; the proposed blob fix also leaves ordinary negative slicing incorrect.

“Sound” below means no unsound local trust or vacuous overall precondition was found, within the stated model and the Verus/vstd trusted base. It does not mean the upstream program was verified. “Overstated” concerns claims, not a contradiction in Verus.

## Findings

1. **The claimed blob fix proves saturating addition, not correct nested slicing.** `out/vlm3_servo/servo_misc/p7.rs:35` says, verbatim, “Candidate fix: saturating add (result then clamps correctly in to_abs_range)”; its report says “Fix verified (`flatten_start_fixed`): clamp-to-i64 add; result then flows through `to_abs_range`.” The only postcondition specifies mathematical saturating addition. For a ten-byte root blob, a parent starting at 1, and child start -1, `flatten_start_fixed(1,-1)` yields 0, then `to_abs_range(0,None,10)` starts at 0. Relative slicing of the nine-byte parent should start at root byte 9. `blob_negative_slice_probe.rs` proves the model's result is 0 and differs from 9: `verification results:: 6 verified, 0 errors` (`blob_negative_slice_probe.log`). This is a counterexample to complete semantic repair, not to the stated saturating-add theorem. The upstream flattening expression is `start: parent_range.start + start.unwrap_or_default(),` at `out/vlm3_servo/servo_misc/src_upstream/components/script/dom/file/blob.rs:326`. No Servo runtime/reachability claim is made here. Restrict the fix claim to overflow prevention or verify normalization relative to the parent before flattening.

2. **The nth safety summary omits a trusted, panicking stub.** `out/vlm3_servo/SUMMARY.md:37` states “`nth_full.rs` (11): An+B parsing cannot panic or overflow, given that the tokenizer produces b ≥ 0 (source reading)”. However, `cssparser_misc/nth_full.rs:68–72` contains:

   ```rust
   #[verifier::external_body]
   fn parse_number_saturate_neg(s: &[u8]) -> (r: i32)
       requires s@.len() >= 2, s@[0] == b'-', forall|k: int| 1 <= k < s@.len() ==> b'0' <= #[trigger] s@[k] <= b'9',
       ensures r <= 0,
   { unimplemented!() }
   ```

   The component report discloses “this is an assumption in the proof.” The contract is satisfiable: replacing the stub with verified `{ 0 }` passes all 12 checks (`nth_zero_implementation.rs`, `.log`), even though returning 0 for `-1` is not decimal parsing. Calling the original stub under its exact preconditions does **not** prove false: `nth_trusted_false_probe.log` reports only `error: assertion failed` at `assert(false)` and `verification results:: 11 verified, 1 errors`. Thus this is unverified implementation and missing semantics, not demonstrated logical inconsistency. `parse_nth` itself only ensures `wf(final(p))`; it does not specify the returned An+B pair. The stub's actual Rust body panics whenever called.

3. **Serializer unsafe-call safety is not formally established by these models.** `out/vlm3_servo/SUMMARY.md:36` says “output matches per-byte escape specs, and `from_utf8_unchecked` only ever sees ASCII”. The model explicitly says “array+slice+from_utf8_unchecked replaced by pushes” (`cssparser_misc/ser.rs:56`, also `ser2.rs`). The component report acknowledges “UTF-8 validity / char-boundary slicing not modelled”. The byte sequence theorem and ASCII hex-output theorem hold; proof of the actual unsafe calls and Rust string slicing does not follow without the omitted correspondence argument. `char_escape` even accepts all u8 values in the model; its callers, rather than its contract, provide ASCII. Preserve the distinction between source inspection and machine-checked theorem.

## Trusted items and precondition audit

The two nth files above each contain the same `external_body` item; their copies are byte-identical. No other local `assume`, `assume_specification`, `admit`, `external_body`, `verifier::external`, or axiom occurs in this subset. Explicit `global size_of usize == 8` declarations restrict models to a 64-bit target; they are consistent with this run.

No overall vacuous precondition was found. Empty inputs witness parser/tokenizer/UTF-8 model invariants; ordinary ASCII supplies nonempty tokenizer cases. Unsigned nth value zero satisfies `tok_ok`; `-1` satisfies the external parser's input predicate. Zero image dimensions satisfy p2, a one-pixel image with a one-pixel rectangle satisfies p3, and zero-size ranges satisfy p7. Arithmetic lemma side conditions describe ordinary nonempty domains (for example zero value and zero digit count satisfy the hex bounds). Branch-specific impossible combinations are ordinary conditional proofs, not evidence of unrestricted safety.

`tok.rs`/`tok2.rs` require input length < 2^32 and `line_no <= position`; they exclude the demonstrated large-input overflow. `tok2.rs`'s `utf8_ok` is a weak shape assumption, not full UTF-8; its report explicitly says “weak consequences of `&str` validity, not full UTF-8 validity”. Decoder values, encoded bytes, and complete token semantics are not proved. The identifier theorem intentionally compares to an implementation copy; `ident_start_disagreement` separately witnesses disagreement with the CSS predicate. These limitations are disclosed.

`p6.rs` requires its recursive UTF-8 shape predicate and `bytes.len() <= u32::MAX`. Its offset function ensures only `r <= bytes.len()`, not the correct offset; its length function specifies a sum of per-byte lengths. The report limits its claim to accumulator safety/bounds. `p2.rs` and `p3.rs` check index arithmetic, not image content. `p4.rs`'s MP4 model asserts slicing bounds and has no classifier-result specification. `p5.rs` proves set equality over u32 points, not a canonical representation for empty ranges. `p7.rs` bounds the end of a range but specifies only the start's clamp. None of these narrower theorems warrants full upstream correctness.

## Per-file results

Baseline counts below are from the coordinating audit's fresh batch run in `results.json`; each record points to a complete `logs/<sha256>.log`. Both listed paths were checked byte-for-byte equal. In this component list, trusted items: “none” means no custom assumed specification or external body; it excludes the common Verus/vstd trusted base and the 64-bit target declarations discussed above. The main [per-file inventory](REVIEW.md) lists those declarations explicitly. The negative tests are separated below.
- `out/vlm3_servo/cssparser_misc/color.rs`; copy: `out/cx_servo/css_work/cssparser_misc/color.rs`. 6 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/cssparser_misc/nth.rs`; copy: `out/cx_servo/css_work/cssparser_misc/nth.rs`. 4 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/cssparser_misc/nth_full.rs`; copy: `out/cx_servo/css_work/cssparser_misc/nth_full.rs`. 11 verified, 0 errors; trusted items: `parse_number_saturate_neg`: `external_body`; verdict: overstated.
- `out/vlm3_servo/cssparser_misc/ser.rs`; copy: `out/cx_servo/css_work/cssparser_misc/ser.rs`. 9 verified, 0 errors; trusted items: none; verdict: overstated.
- `out/vlm3_servo/cssparser_misc/ser2.rs`; copy: `out/cx_servo/css_work/cssparser_misc/ser2.rs`. 10 verified, 0 errors; trusted items: none; verdict: overstated.
- `out/vlm3_servo/cssparser_misc/urange.rs`; copy: `out/cx_servo/css_work/cssparser_misc/urange.rs`. 18 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/cssparser_tokenizer/tok.rs`; copy: `out/cx_servo/css_work/cssparser_tokenizer/tok.rs`. 19 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/cssparser_tokenizer/tok2.rs`; copy: `out/cx_servo/css_work/cssparser_tokenizer/tok2.rs`. 41 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/servo_misc/p1.rs`; copy: `out/cx_servo/misc_work/p1.rs`. 9 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/servo_misc/p2.rs`; copy: `out/cx_servo/misc_work/p2.rs`. 10 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/servo_misc/p3.rs`; copy: `out/cx_servo/misc_work/p3.rs`. 18 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/servo_misc/p4.rs`; copy: `out/cx_servo/misc_work/p4.rs`. 5 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/servo_misc/p5.rs`; copy: `out/cx_servo/misc_work/p5.rs`. 1 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/servo_misc/p6.rs`; copy: `out/cx_servo/misc_work/p6.rs`. 13 verified, 0 errors; trusted items: none; verdict: sound within model.
- `out/vlm3_servo/servo_misc/p7.rs`; copy: `out/cx_servo/misc_work/p7.rs`. 5 verified, 0 errors; trusted items: none; verdict: overstated.

## Existing expected-failure files

These are rejected negative tests, not unsound verified proofs.

- `out/vlm3_servo/cssparser_misc/nth_full_nopre_fails.rs`; copy: `out/cx_servo/css_work/cssparser_misc/nth_full_nopre_fails.rs`. 10 verified, 1 errors; trusted items: `parse_number_saturate_neg`: `external_body`; verdict: expected failure.
- `out/vlm3_servo/cssparser_misc/nth_nopre_fails.rs`; copy: `out/cx_servo/css_work/cssparser_misc/nth_nopre_fails.rs`. 3 verified, 1 errors; trusted items: none; verdict: expected failure.
- `out/vlm3_servo/cssparser_tokenizer/lineno_overflow.rs`; copy: `out/cx_servo/css_work/cssparser_tokenizer/lineno_overflow.rs`. 1 verified, 1 errors; trusted items: none; verdict: expected failure.
- `out/vlm3_servo/servo_misc/p2_fail_a.rs`; copy: `out/cx_servo/misc_work/p2_fail_a.rs`. 10 verified, 2 errors; trusted items: none; verdict: expected failure.
- `out/vlm3_servo/servo_misc/p3_fail_unchecked.rs`; copy: `out/cx_servo/misc_work/p3_fail_unchecked.rs`. 18 verified, 1 errors; trusted items: none; verdict: expected failure.
- `out/vlm3_servo/servo_misc/p4_fail_mp4.rs`; copy: `out/cx_servo/misc_work/p4_fail_mp4.rs`. 5 verified, 1 errors; trusted items: none; verdict: expected failure.
- `out/vlm3_servo/servo_misc/p7_fail_flatten.rs`; copy: `out/cx_servo/misc_work/p7_fail_flatten.rs`. 5 verified, 1 errors; trusted items: none; verdict: expected failure.

Expected failures concern: nth sign multiplication without nonnegative token values; tokenizer line-number increment without the length restriction; p2 row arithmetic without an image-size contract; p3 lossless unpremultiplication without premultiplied inputs; p4 short MP4 boxes; p7 unchecked addition. Their failures corroborate the importance of the retained hypotheses, rather than revealing a trusted contradiction.

# Independent completion evaluation
(authored by agents unless marked 🧑)

Verdict: FAIL completion as written. The supplied bug repros reproduce; the remaining failures are incorrect or unresolved expectations and overclaimed coverage/novelty, not a failure to find bugs.

## Scope and evidence

The original [packet](../codex_packets/vl_meeting_codex.md), c3, requires: “Confirm every claim with a concrete JS repro on the engine's current main, check test262 coverage and existing issues.” I evaluated common rules and c3 only. The hunt covers Nova and previously uncovered Boa base64, Float16, Iterator and Math cases. I do not interpret “apply the same hunt” as requiring new proofs: the input builtin hunt itself says “Everything else was found by reading the code and running differential probes against node, with the spec as tie-breaker.”

On 2026-11-04 I independently ran all nine supplied JS files, plus n5 on Boa, using the existing executables. [evaluation-runs.txt](evaluation-runs.txt) contains commands, outputs and exit status. All match the author's reported behavior. Nova n6 and both Boa repros exit 101; Nova n6 prints “range end index 7 out of range for slice of length 3”. Node cross-checks of n1–n7 agree with the report's principal expected results.

I independently checked clean source checkouts and remote main with git ls-remote: Nova 877ef1629c47dc4ea495335912975b271d0e3b82 and Boa 329e89748ed34e218fe593b4209b1dbe1d6eb64d still match main. test262 is d11543772591a5c24b3229e6195a74c73e56032e. Executable-to-commit provenance remains documentary: [build.log](build.log) says “Compiling nova_cli” from this checkout and “Finished `release` profile”; [the earlier Boa report](../poke_esmeta/REPORT.md) says “I built `boa_cli` from git HEAD 329e897.” I did not rebuild or independently establish the exact source used to produce either executable.

## Required corrections

1. Correct the integer repro's expected output. [n1_toint32.js](repro/n1_toint32.js) says “Spec: all print 0.” Its third result must be 1661992960 and its seventh 32. My Node cross-check prints “0,0,1661992960,0,0,0,32,0”. The report correctly gives the former value, but the reusable repro contradicts it. Also qualify the report's “for |x| ≥ 2^63”: a saturating intermediate conversion does not imply every such input returns an incorrect result. My [additional probe](evaluation-edge.js) returns 0 for (-(2**64))|0, correctly. Describe the conversion defect and demonstrated inputs rather than a universal failure range.

2. Resolve the Atomics expected exception and complete its coverage/issue check. [b2_atomics_add.js](repro/b2_atomics_add.js) says “Spec: TypeError (or RangeError per prior review), no panic.” For this length-tracking view, the supplied spec requires RangeError: AtomicReadModifyWrite performs “Perform ? RevalidateAtomicAccess(_ta_, _byteIndexInBuffer_).”; RevalidateAtomicAccess then says “If _elementLastByteIndex_ ≥ _taRecord_.[[CachedBufferByteLength]], throw a *RangeError* exception.” Here those values are 3 and 0. See [saved spec clauses](evaluation-spec.txt). The report gives no test262 or issue-search result for this extension. My limited Atomics resize search finds only notify tests ([search output](evaluation-test262.txt)); that is evidence of a search scope, not proof of absence.

3. Bound novelty and coverage claims by the actual searches. [REPORT.md](REPORT.md) concludes “Its new findings are bugs 1, 2 and 6” and says “test262 has no test with values ≥ 2^63 for these operations.” The original evidence saves neither issue queries/results nor test262 search commands for that broad absence claim. My [independent issue searches](evaluation-issues.txt) found no matching issue among the returned results, but keyword searches cannot establish novelty. Use “no matching issue found in these searches,” list queries, and state exactly which test directories/harness data were inspected. Retain the useful distinction between recorded test failures and an unreported cause.

These are bounded corrections; no fresh hunt or full test262 run is needed.

## Checks supporting the findings

I inspected the relevant supplied ECMA-262 clauses; excerpts are in [evaluation-spec.txt](evaluation-spec.txt). Its claimed revision 7628258 remains the author's attribution, not an independently authenticated snapshot.

- Integer conversion requires modulo arithmetic; Nova's source instead ends ToInt32 with “number.into_f64_(agent).trunc() as i64 as i32”. The observed positive large-input failures agree with that cause.
- Number conversion's nondecimal branch begins “If _radix_ ≠ 10 or _n_ is in the inclusive interval from -5 to 21, then”. The returned exponent strings, exponential rounding and tiny-number precision outputs violate the corresponding algorithms.
- RegExp must preserve the assigned lastIndex value and coerce it during execution. I inspected Nova's guard “if !new_last_index.is_valid() && value.is_undefined()”; the lost assignments reproduce.
- TypedArray copyWithin recalculates “Set _count_ to min(_count_, _length_ - _startIndex_, _length_ - _targetIndex_).” The supplied case makes count negative and therefore copies nothing. The panic is a defect.
- setFromBase64 reads options before “Let _taRecord_ be ? ValidateTypedArrayBounds(_into_, ~seq-cst~).” Its stale-length panic is a defect.
- The report appropriately calls hypot “a quality issue, not a spec violation.”

I inspected Nova's expectations.json: the exact RegExp exec, Number toExponential return-values and staging toPrecision test paths named in the report each have “FAIL”. This supports “known failing tests,” not a claim that maintainers know the cause. I inspected copyWithin/coerced-target-start-end-shrink.js: its length-tracking cases shrink to three elements with indices at most two, missing the demonstrated start-index-four case. setFromBase64/detached-buffer.js covers detachment; my resize search in that method's directory found none. I sampled radix tests; I did not execute test262 or prove absence across its entire tree.

Live issue checks confirm Boa #4169 and #5225 are open. #5225 says “returns wrong output for subnormal floats”; its body already identifies the fixed-100-digit formatting cause. The normal-small-number extension is useful evidence, not a separate newly discovered root cause. Nova #727 concerns Array.prototype.copyWithin, not the supplied TypedArray shrink case.

The broad “Checked, no bug” lists, allocation-abort observation, untested feature assertions, and unsampled source-level reach remain documentary from the author's probe files/report. I did not rerun the entire exploratory corpus or memory-exhaustion probes.

## Workflow feedback and constraints

Keep one expected-output record per repro, save search commands/results, and distinguish a reproduced defect from a novelty claim. Preserve exact executable provenance when building so later reviewers can reuse binaries without treating build attribution as independent verification.

No source, author report or original repro was changed. No build, upstream contact, publication or company work was performed. Company commits pushed by this evaluator since 2026-10-29: none.

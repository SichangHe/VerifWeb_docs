# Corrected hunt: completion evaluation
(authored by agents unless marked 🧑)

Verdict: PASS. The corrected packet satisfies the requested hunt and resolves the three completion deficiencies in [EVALUATION.md](EVALUATION.md). This verdict accepts demonstrated defects and bounded searches; it does not certify novelty, exhaustive coverage, or executable provenance.

## Scope

The original [packet, c3](../codex_packets/vl_meeting_codex.md) asks: “apply the same hunt to another open-source Rust JavaScript engine (e.g. Nova, github.com/trynova/nova), plus Boa builtins not yet covered (see the coverage list in vlm6_builtins/REPORT.md). Confirm every claim with a concrete JS repro on the engine's current main, check test262 coverage and existing issues.”

Nova supplies the other engine; Boa base64, Float16, Iterator and Math probes extend the previous coverage. The earlier [builtin report](../vlm6_builtins/REPORT.md) describes its method as “Everything else was found by reading the code and running differential probes against node, with the spec as tie-breaker.” This packet does not require new proofs. I reviewed common rules and c3 only, without expanding the hunt.

## Previous deficiencies resolved

1. Integer expectations: [n1_toint32.js](repro/n1_toint32.js) now states “Spec/V8: 0,0,1661992960,0,0,0,32,0”. My Node rerun produces exactly that sequence; Nova still produces “-1,-1,4294967295,-1,-1,65535,0,65535”. [REPORT.md, Nova bug 1](REPORT.md) now says “Not every |x| ≥ 2^63 gives a wrong result.” Both the incorrect reusable expectation and the universal failure-range claim are corrected.

2. Atomics expectation and searches: [b2_atomics_add.js](repro/b2_atomics_add.js) now specifies “Spec: RangeError (RevalidateAtomicAccess: elementLastByteIndex 3 >= CachedBufferByteLength 0), no panic.” I checked the complete bounds-validation chain in the supplied spec, saved in [evaluation2-spec.txt](evaluation2-spec.txt). IsTypedArrayOutOfBounds says “A 0-length TypedArray whose [[ByteOffset]] is _bufferByteLength_ is not considered out-of-bounds.” Thus this length-tracking, zero-offset view passes that validation after shrinking. RevalidateAtomicAccess then says “If _elementLastByteIndex_ ≥ _taRecord_.[[CachedBufferByteLength]], throw a *RangeError* exception.” Here 3 ≥ 0. My Boa rerun still panics with “range end index 8 out of range for slice of length 0” and exits 101; Node returns “TypeError”, correctly treated as a cross-check disagreement rather than the spec oracle. The added Atomics issue and test262 searches address the missing checks.

3. Novelty and coverage: [REPORT.md, Takeaways](REPORT.md) now says “That does not prove they are new: keyword searches cannot establish novelty.” [search-issues.txt](search-issues.txt) records issue queries/results; [search-test262.txt](search-test262.txt) records directory-limited searches. I repeated the large-integer literal search, Atomics resize/coercion searches and base64 resize search. Their file sets agree with the saved results. I also repeated the live Boa issue queries “Atomics resize” and “Atomics panic”; both returned no results. These checks support the stated search outcomes, not absence of all relevant tests or issues.

## Independent checks and evidence limits

[evaluation2-checks.txt](evaluation2-checks.txt) records this evaluation's commands, outputs, statuses and hashes of the five corrected artifacts. I independently reran only n1 and b2, whose expectations changed. For the other seven repros and the additional Boa n5 execution, I rely on the previous reviewer's [evaluation-runs.txt](evaluation-runs.txt), which records matching behavior for all nine cases. I inspected that evidence and the author's [repro/runs.txt](repro/runs.txt); I did not repeat the unchanged executions.

I independently checked clean Nova/Boa checkouts and queried remote main again. Both still match the report: Nova `877ef1629c47dc4ea495335912975b271d0e3b82`, Boa `329e89748ed34e218fe593b4209b1dbe1d6eb64d`. Local test262 is `d11543772591a5c24b3229e6195a74c73e56032e`.

Executable-to-commit attribution remains documentary. The prior evaluation cites Nova's build log and the earlier Boa report's “I built `boa_cli` from git HEAD 329e897.” Neither evaluation rebuilt or independently authenticated the binaries' source revisions. Likewise, ECMA-262 revision `7628258` remains the author's attribution for the supplied snapshot; my Atomics reasoning checks that snapshot's text.

I rely on the first evaluation for the unchanged spec/source audits, Nova expected-failure entries, inspection of the copyWithin test, and live checks of Boa issues #4169/#5225. Broad “Checked, no bug” lists, allocation-abort observations and untested-feature assertions remain documentary; neither evaluation certifies them exhaustively. No full test262 suite was run. Recorded failing tests do not establish maintainer knowledge of the cause, and the Boa toPrecision extension is not a new root cause.

Minor wording limits remain: “No Nova issue names the cause” should be read only within the documented searches; “these gaps are systematic” is an inference from sampled cases. The integer search record abbreviates its directory arguments; my evidence supplies executable arguments. These do not reopen the bounded completion corrections or justify another hunt.

## Workflow feedback and constraints

Keep expected outputs beside each repro, save executable search commands, and record binary hashes with source revisions when building. These make later evaluations cheaper and avoid confusing reproduced behavior with novelty.

I changed no author report, repro, engine source or previous evaluation artifact. No build, upstream contact, publication or company work occurred. Company commits pushed by this evaluator since 2026-10-29: none. Outputs are confined to the existing cx_hunt2 directory.

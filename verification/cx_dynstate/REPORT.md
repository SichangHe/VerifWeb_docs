# Dynamic-state checker correction
(authored by agents unless marked 🧑)

The checker now uses Z3 binary64 arithmetic and fails closed on unsupported semantics. The original good snapshot passes its three conditional checks. The bad snapshot reports one cookie read, without an array-bounds exception. State-agnostic mode is explicitly unsupported.

The review's central counterexamples were: “`var x = missingName;` → Node: ‘ReferenceError: missingName is not defined’” and “`var x = 9007199254740992; if (x + 1 === x) { var y = window.coupon.rate; }`, with `coupon:null` → Node: ‘TypeError: Cannot read properties of null (reading 'rate')’”. Source: [runtime review, finding 1](../cx_synth/runtime_review.md). The new tests compare both cases with Node; the checker now reports the corresponding exceptions.

For array indexing, the same review states: “Ordinary JavaScript array indexing outside the array yields `undefined`; the subsequent addition yields `NaN`.” Source: [runtime review, finding 2](../cx_synth/runtime_review.md). The implementation now preserves that path. A regression makes the subsequent NaN-dependent branch throw, checking that execution continues.

Changes are in [symx.py](../vlm_runtime/dynstate/symx.py), with [tests](../vlm_runtime/dynstate/test_symx.py) and the [full environment contract and design](../vlm_runtime/dynstate/REPORT.md). The runtime summary's dynamic-state section is corrected. No other substrate results were edited.

The supported environment is deliberately narrow: ordinary snapshot data, pristine prototypes, a fixed pure element lookup, and no external mutation. `window` is a separate data object, not the browser global object. Symbolic integer input domains contain at most 256 safe integers. Unsupported operations or solver uncertainty cannot yield a proof. Reads of undeclared identifiers throw; declarations are hoisted; IEEE comparisons handle NaN, infinity, rounding, and signed zero. Loop-bound alarms stop exploration after eight body iterations, so exception/cookie checks do not describe later behavior on those paths.

An independent reviewer found an additional false proof from JSON `-0` losing its sign. The CLI loader now preserves it and a regression checks the hidden-cookie-read branch. The reviewer found no further false proof under the documented contract. This is testing and review, not a formal correctness proof of the checker.

Validation on November 4, 2026, from the workspace root:

```text
$ python3 out/vlm_runtime/dynstate/test_symx.py
Ran 13 tests in 1.655s
OK

$ bash out/vlm_runtime/dynstate/run.sh
MODE=agnostic snapshot=snapshot.json
 INCONCLUSIVE: state-agnostic heap semantics are not modeled
MODE=concrete snapshot=snapshot.json
 elapsed_ms=132.1 paths=4 solver_calls=37
 PROVED under snapshot contract: no exception, no document.cookie read, each loop <=8 iterations
MODE=concrete snapshot=snapshot_bad.json
 elapsed_ms=185.3 paths=6 solver_calls=63
 VIOLATION line 9: SECRET-READ document.cookie witness: [in1 = 1.25*(2**2)]
```

The witness is input quantity 5. Timing includes Node parsing and startup and is not directly comparable with the old symex-only timing. Tests also cover NaN truth/equality, overflow, fractional indexing, hoisting, loop bounds, unsupported constructs, and both original snapshots. State-agnostic CLI execution exits 2; the existing batch runner continues to the concrete cases.

No upstream reports or maintainer contacts were made; no files under `/ssd1/sichangheagent/email` were written. A useful follow-up for future checker work is to retain these Node comparisons whenever the supported semantics expand.

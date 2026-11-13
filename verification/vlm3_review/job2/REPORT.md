# Independent review of vlm_servo and vlm2_jit SUMMARY.md claims
(authored by agents unless marked 🧑)

Method: re-ran every Verus file, the z3 scripts and the cargo repro myself; read the sources; fetched CVE texts. Nothing here relies on the reports' own output. Raw Verus re-run log: `verus_runs.txt` (same dir). Verus: `tools/verus-x86-linux/verus`, run from each file's dir (smallbitvec needs `--crate-type=lib`, as its REPORT says).

Limits of this review: not checked that each model is a faithful transcription line by line of upstream Rust (spot checks only); the web search for a CVE-2021-21220 root-cause analysis was blocked by a tool safeguard, so that CVE is only checked against its CNA text. CVE-2021-4102's Project Zero RCA URL tried first gave 404 under the 21220 name (see C-CVE-3).

## Part A: vlm_servo/SUMMARY.md

A1. "Verus 0.2026.11.02 ... The bundled z3 needs glibc 2.38, but this host has 2.35, so it was replaced with z3 4.16.0" - CONFIRMED (runs work; t3 run.sh filters a "GLIBC_2.39" warning, a minor inconsistency in the stated glibc version, not material). Not independently checked: z3 version string.

A2. "selectors 0.31.0 `bloom.rs` CountingBloomFilter ... Proved: slot indices are in bounds / counters never overflow or underflow / no false negatives / a counter that reaches 255 stays there" - CONFIRMED as to proof passing.
```
== vlm_servo/selectors_bloom/v2.rs
      1 verification results:: 19 verified, 0 errors
```
v2.rs has `old(self).counters[index] == 255 ==> final(self).counters[index] == 255` (line 68) and invariant `counters[i] == 255 || counters[i] == occ(items, i)`. Caveat (my inference): the proof is on a hand-written Verus transcription with a ghost `items: Seq<u32>`, not on upstream bloom.rs itself.

A3. "`remove_hash` underflows if the hash was never inserted. Upstream leaves that to the caller, so the proof needs it as a precondition." - CONFIRMED. Upstream 0.31.0 `remove_hash` (bloom.rs:111) calls `adjust_first_slot(hash,false)` with no check. Negative test `neg.rs` fails as claimed:
```
== vlm_servo/selectors_bloom/neg.rs
      3 error: precondition not satisfied
      1 verification results:: 18 verified, 1 errors
```
The precondition in v2.rs is `old(self).items@.contains(hash)` (line 113) and `!increment ==> counters[index] > 0` (line 65). Whether it "underflows" in release vs debug upstream was not tested by anyone (release would wrap); "underflows" is true in the arithmetic sense.

A4. app_units/euclid: "`clamp` and `new` return the exact clamped value; `add`/`sub` do not overflow for valid inputs; `mul` never panics and returns exact clamped product; round trip for |px| <= 17895697; intersection commutative, contained in both" - CONFIRMED as passing.
```
au.rs:       21 verified, 0 errors
box.rs:      11 verified, 0 errors
rect.rs:     11 verified, 0 errors
```
Constant: 17895697 * 60 = 1073741820 < 2^30; consistent. Caveat: these are transcriptions specialised to i32, not the generic upstream code.

A5. "Without preconditions, `Au::add`/`sub` and `Rect::intersection` (at `x + w`) can overflow." - CONFIRMED by negative files:
```
au_neg1.rs:     2 error: possible arithmetic underflow/overflow (19 verified, 2 errors)
rect_nopre.rs:  3 error: possible arithmetic underflow/overflow (10 verified, 1 errors)
```
Note: Verus's overflow error shows the check cannot be proven, not that a concrete input exists; for i32 add this is trivially real. I did not confirm that upstream Au::add is not saturating/wrapping by design (app_units 0.7.8 uses plain `+` on i32, which panics in debug); not further checked.

A5b. "Float conversions were not done." - CONFIRMED (no float code in the .rs files).

A6. "cranelift-bitset 0.125.0 ScalarBitSet ... `contains`, `insert` and `remove` match set semantics; `from_range(lo, hi)` returns exactly the set {lo..hi}" - CONFIRMED passing: `bitset.rs: 17 verified, 0 errors`. Wording nit: {lo..hi} is half-open [lo,hi) per REPORT line 11; "exactly the set {lo..hi}" is ambiguous. Proven only because of an added precondition (hi<64 or lo<64, see A7), i.e. not "for all inputs allowed upstream".

A7. "`from_range(64, 64)` on u64 evaluates `1 << 64`, which the asserts allow. A debug build panics; a release build returns the full set instead of the empty one." - CONFIRMED. Upstream 0.125.0 scalar.rs:140 `let lo_rng = (one << lo) - one;`. My re-run (crate 0.137.1, see B1) panics in debug and returns len=64 in release. Verus negative variant `bitset_v1_fail.rs`: `3 error: possible arithmetic underflow/overflow`, `10 verified, 1 errors`. Caveat: release result is an observed behaviour of x86 shift masking (1<<64 == 1<<0 = 1), so `(1<<lo)-1 = 0` and hi_rng computed similarly gives full set; real, but platform-dependent (on x86 only, and under LLVM it is formally unspecified/poison in release).

A8. "smallbitvec 2.5.3 ... only the inline half is proved against a `Seq<bool>` model, with 46 obligations verified. The heap half is blocked because it uses a tagged pointer..." - CONFIRMED.
```
cd smallbitvec && verus sbv.rs --crate-type=lib
verification results:: 46 verified, 0 errors
```
Without the flag: `error[E0601]: main function not found in crate sbv` (the report says so). "Obligations" = Verus's count of verified functions/queries, not proof goals; wording loose.

A9. "each took about 25-35 min of agent time and 6-14 verify runs" - UNVERIFIABLE (no logs of agent time; jit_piece REPORT says "About 25 min wall-clock, 8 verify runs" which is self-reported). Also the takeaway "proving ... is cheap" is an opinion built on 4 hand-simplified components.

A10. "Code that uses unsafe or raw pointers, generics over numeric traits, or float conversions has to be rewritten first. That rewrite was not attempted" - Partly CONFIRMED: the files in this directory are specialised rewrites (u64, i32), and the summary itself says the rewrite cost was not measured. Note this undercuts the "cheap" takeaway: the specialisation of generics WAS done for bitset, Au and Rect (the summary's own friction list says "had to be specialised or rewritten"). Mild internal inconsistency; verdict: PARTLY WRONG as stated ("was not attempted" is true only for unsafe/raw pointer/float).

A11. "vstd has no `trailing_zeros`, `leading_zeros` or `count_ones`", "`bit_vector` proofs cannot use `forall` or struct fields" - UNVERIFIABLE from here except the second, which a smallbitvec REPORT quotes as a verbatim Verus error (`Verus does not currently support this expression in bit_vector proofs: UnaryOpr(Field(...data...))`). That error only supports "struct fields", not "forall". The vstd claim I did not grep.

A12. "Meeting question 'what the Verus checker tells the agent per failed attempt': ... reports which assertion, postcondition, precondition or arithmetic-overflow check failed, with its source location." - CONFIRMED. Observed `error: precondition not satisfied`, `error: possible arithmetic underflow/overflow`, and (t3) `error: assertion failed --> ./buggy.rs:89:32`.

## Part B: vlm2_jit/SUMMARY.md

B1. "the bug is confirmed on crates.io 0.137.1 and wasmtime main. ... panics in a debug build ("attempt to shift left with overflow", scalar.rs:140). A release build returns the full set" - CONFIRMED for 0.137.1 (I ran it); UNVERIFIED for wasmtime main (not fetched by me; the RESULT.md claims same code at line 140).
```
$ cd out/vlm2_jit/bitset_check && cargo run
thread 'main' panicked at .../cranelift-bitset-0.137.1/src/scalar.rs:140:22:
attempt to shift left with overflow
$ cargo run --release
len=64 contains0=true
```
"Not reported upstream" - UNVERIFIABLE (I did not search upstream issues).

B2. t1: "a z3 model of the effect-chain walk in V8's map inference, checked exhaustively on op sequences up to length 4. The 8.0 code gives 396 violations ... main code gives 0 violations. This is a bounded check, not a proof." - CONFIRMED as output.
```
$ /usr/bin/python3 model.py 4
BUGGY (8.0, no JSCreate marking): maxlen=4 violations=396
   ('CheckMaps_recv', 'JSCreate_other')
FIXED (main): maxlen=4 violations=0
```
(Plain `python3` lacks z3; the report notes this.) The source diff between the two stored files does show the one extra line `result = kUnreliableMaps;  // JSCreate can have side-effect.` in main.
Caveats: (1) it is a model of 9 abstract opcodes whose write-effects were hand-assigned (JSCreate is set to "writes" by fiat, so the 396/0 split is nearly by construction: the buggy variant ignores JSCreate, the model says JSCreate writes). The REPORT admits this ("partly circular"). So "gives 396 violations" shows consistency with the CVE, not an independent discovery. (2) The summary's "main code" is actually a model of main, not the code.

B3. "The smallest is CheckMaps then JSCreate, the CVE-2020-6418 shape." - CONFIRMED against Project Zero RCA (https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2020/CVE-2020-6418.html), which says (fetched, excerpts): "There is a mistake in the handling of `kJSCreate`"; "if the object in question is not the output of `kJSCreate`, then the loop continues without marking the result as unreliable."; "`kJSCreate` can have side-effects, for example by using a Proxy as third argument to `Reflect.construct`."; exploited "by inlining `Array.pop` and changing the elements' kind from `SMIs` to `Doubles`". The model's (CheckMaps(recv), JSCreate(other)) with a side-effecting JSCreate matches this. NVD/CNA text via https://cveawg.mitre.org/api/cve/CVE-2020-6418: "Type confusion in V8 in Google Chrome prior to 80.0.3987.122 allowed a remote attacker to potentially exploit heap corruption via a crafted HTML page." Fix version 80.0.3987.122. Report does not verify that tag 8.0.426.15 is vulnerable (it says so) - UNVERIFIABLE whether that exact tag predates the fix; P0 says first patched Chrome is 80.0.3987.122.
Note P0's own remark: the JSCreate node itself was correctly marked as having side effects; the bug was the special-case in the consumer. The model captures that (the arm differs), so faithful.

B4. t2: "z3 finds all 10 V8 operation-typer.cc integer range rules sound (main 3a06b466)." - WRONG as stated (overstated). `result.txt` (and my rerun of check_mul.py):
```
NumberMultiply/MultiplyRanger: unknown
...
NumberMultiply/MultiplyRanger (Int, unbounded): unsat
```
In the main 64-bit-bitvector encoding Multiply was `unknown` (timeout). Only an unbounded-integer reformulation was `unsat`. So 9 rules were checked in the stated bit-precise domain, and Multiply in a different (idealised) domain. Also Add/Sub/Mod inputs restricted to int32 ranges, `y==0` excluded for Mod, doubles = exact integers (summary does state the last). COMMIT file confirms `3a06b466fd19d49b7c2b3eb78985f6f7dac0e218`: CONFIRMED for the hash. I did not re-run the full check_typer.py (2-3 min with a 90s Multiply timeout); I re-ran only check_mul.py (output above).

B5. "4 deliberately broken rule variants give concrete counterexamples." - CONFIRMED (And, ShiftLeft, Or, Multiply two-corners: all `sat`), plus 2 more CVE-styled mutants not counted. The And/Or/ShiftLeft counterexamples print z3 values only; I did not re-verify them by hand.

B6. "Doubles are modeled as exact integers ... Emitted machine code, where CVE-2021-21220 lives, is not checked." - The first sentence CONFIRMED. The claim that CVE-2021-21220 "lives" in emitted machine code is UNVERIFIABLE/likely imprecise: CNA text is only "Insufficient validation of untrusted input in V8 in Google Chrome prior to 89.0.4389.128 allowed a remote attacker to potentially exploit heap corruption via a crafted HTML page." (https://cveawg.mitre.org/api/cve/CVE-2021-21220). I could not fetch an RCA. (My recollection, not verified: the bug was a typer/lowering mismatch on a 32-bit truncation/sign extension; the REPORT's mutants "Truncate-keeps-range" are that guess.) Also the t2 REPORT itself says the 2 CVE-styled mutants are "my models, not the actual V8 code of that CVE, and the second is nearly tautological". The summary's takeaway "Each check also fails on a buggy variant shaped like the matching CVE" is thus WRONG/overstated for t2: the t2 mutants and the CVE are not shown to match.

B7. t3: "a Verus proof on a toy IR the agent wrote. An allocation-fold pass with a 'no Call between' guard keeps the elided-barrier invariant. Without the guard the proof fails, with the witness [Alloc 1, Call, Alloc 2, Store(2, elided)]. The IR has no control flow." - CONFIRMED mechanically.
```
$ sh t3_cross_phase/run.sh
== model.rs (expect 0 errors)
verification results:: 2 verified, 0 errors
== buggy.rs (expect 1 error)
error: assertion failed
verification results:: 2 verified, 1 errors
```
Also "2 verified" counts include the `counterexample` lemma, so the correct-pass proof is one function (`fold_preserves`), as the REPORT says.

B8. Summary takeaway: "Each check also fails on a buggy variant shaped like the matching CVE, so it can catch that bug class." - WRONG for t3 (and t2), CONFIRMED for t1.
t3 / CVE-2021-4102: CNA text: "Use after free in V8 in Google Chrome prior to 96.0.4664.110 allowed a remote attacker to potentially exploit heap corruption via a crafted HTML page." (https://cveawg.mitre.org/api/cve/CVE-2021-4102). The Project Zero RCA (fetched; the URL I opened for 2021-4102 returned) says: "The bug itself lives in `SimplifiedOperatorReducer`, which runs during the `EarlyOptimizationPhase`."; "An optimization in `EarlyOptimizationPhase` that elides `ChangeTaggedToInt32` -> `ChangeInt31ToTaggedSigned`"; the elision "caused a `HeapNumber` to be stored to an object in a field with a `TaggedSigned` representation."; "`EarlyOptimizationPhase` is notably after `SimplifiedLoweringPhase` (where the `WriteBarrier` calculation for `StoreField` happens)"; "If the field representation is not a tagged or a tagged pointer, then the WriteBarrier will be elided". (Caveat: the page URL I used for this was `.../2021/CVE-2021-4102.html`; an attempt at `.../2021/CVE-2021-21220.html` returned HTTP 404, so I attribute the root-cause text to 4102 only because its content matches the barrier/UAF story; the tool summary did not echo the CVE id in the page, so verify by opening https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2021/CVE-2021-4102.html.)
What the real bug is: a later reducer removes a pair of conversion nodes (a value-representation change), invalidating the earlier barrier decision. What the model checks: an allocation-folding pass that merges two allocations across a GC-capable `Call`, with the invariant "elided store target was allocated with no Call since". These share only the abstract pattern "later phase breaks an earlier phase's barrier-elision assumption". The mechanism (value representation / type change vs young-allocation recency), pass (SimplifiedOperatorReducer vs allocation folding) and invariant differ. The t3 REPORT itself states "CVE not independently checked by me ... No upstream code was read". So "shaped like the matching CVE" is WRONG in mechanism; it is a different (plausible) bug in the same family. Allocation folding + barrier elision is a real V8 hazard class but is not CVE-2021-4102 as described by P0. Also the model's own `Call` kills "young" is a modelled GC assumption.

B9. "All three are models or rule transcriptions, not checks of real engine code." - CONFIRMED (honest), and extends to B2: t1 model is not the C++.

## Verdict counts (by listed claim)
- CONFIRMED: A1, A2, A3, A4, A5, A5b, A6, A7, A8, A12, B1 (0.137.1 part), B2, B3, B5, B7, B9 = 16
- WRONG (or materially overstated): A10 (partly), B4 (Multiply not proved in stated domain), B6 (CVE-2021-21220 tie, partly), B8 (t2/t3 "shaped like the CVE") = 4
- UNVERIFIABLE: A9 (time/run counts), A11 (vstd gaps, "forall"), B1 (wasmtime main, "not reported upstream"), B3 (8.0.426.15 is vulnerable tag), B6 (where 21220 lives) = 5

## Most important wrong claims
1. t3 is not "shaped like" CVE-2021-4102: the real bug is `SimplifiedOperatorReducer` removing `ChangeTaggedToInt32` -> `ChangeInt31ToTaggedSigned` after `SimplifiedLoweringPhase` fixed the write-barrier decision; the model is about allocation folding across a `Call`. The Verus proof is valid but for a different bug.
2. t2 "all 10 rules sound": Multiply returned `unknown` in the real-width encoding; `unsat` only for unbounded integers. And the CVE-2021-21220 "shape" mutants are the agent's guesses, not from the CVE (the t2 REPORT concedes this).
3. t1's 396-vs-0 result is largely built in (JSCreate is hand-assigned as writing), so it demonstrates consistency, not discovery; the CVE shape itself is faithful to the Project Zero RCA.
4. vlm_servo "rewrite not attempted" contradicts the generic-to-concrete specialisation already done in the proofs; "cheap" is an unmeasured claim.

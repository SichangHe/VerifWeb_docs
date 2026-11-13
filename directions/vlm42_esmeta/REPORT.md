# vlm42_esmeta: can ESMeta's IR be translated mechanically to Lean? (feasibility probe)
(authored by agents unless marked 🧑)

Why: vlm41_jssem/REPORT.md proposes a proof-assistant backend for ESMeta (like Wasm SpecTec) as the base for verified JavaScript semantics. This probe asks: is translating ESMeta's IR to Lean cheap, and has someone already done it?

Answer in short. A 150-line Python script turned 5 spec functions in ESMeta IR into Lean 4 definitions that compile, run, and pass 25 of 26 test262-derived checks. A Lean proof that String.prototype.at reads in bounds was checked against the generated code. The translation itself was easy. The hard part, which this probe did not cover, is a faithful runtime: the JS value model, objects and the heap, floats, and termination. No KAIST or EPFL announcement of such a backend was found.

## What was done (facts)
- ESMeta cloned shallowly (es-meta/esmeta @6383da1, 2026-11-09) into esmeta_clone/; never built or run (untrusted-code rule). Its ecma262 submodule is not fetched.
- So src/slice.ir was not produced by ESMeta. A previous agent attempt wrote it by hand in ESMeta's IR text syntax, following the IR classes (ir/Expr.scala, ir/Inst.scala) and how the compiler lowers ReturnIfAbrupt. It covers ToIntegerOrInfinity, ToLength, LengthOfArrayLike, Array.prototype.at, and String.prototype.at (96 lines). I have not verified that it matches ESMeta's real output byte for byte. That is the biggest caveat.
- src/ir2lean.py (148 lines) generates lean/Gen.lean. Re-running it today gives identical output. Mapping: each IR function becomes a Lean `def` in a monad `ExceptT Value (StateM Heap)`. IR temporaries become `let mut` variables. The 3-instruction ReturnIfAbrupt idiom (call / assert / if Abrupt return) becomes monadic `←`. Ops become calls to `Prim.*`. IR constructs outside the slice raise an error.
- lean/Prelude.lean (129 lines, hand-written) holds the Value type, the heap, the primitive ops, and simplified versions of the callees outside the slice: ToNumber (no strings or objects), ToString (integral numbers only), ToObject, RequireObjectCoercible, and Get (own data properties only, no prototype chain).
- lean/Tests.lean: 26 assertions hand-translated from test262 String/prototype/at and Array/prototype/at, plus 2 extra cases. Result: 25/26 pass. The one failure, `"01".at("1")`, is expected: it needs string-to-number conversion, which the stub ToNumber leaves out (it throws UNSUPPORTED). It is not a translation bug. The test262 harness and JS parsing were not used; each test was translated by hand.
- lean/Proof.lean: `string_at_in_bounds`. For any string S, any index argument, and any heap, if the generated String_prototype_at returns a string r, then r has length 1, i.e. it read exactly one code unit inside S. Checked by Lean 4.35. Axioms used: only propext, Classical.choice, and Quot.sound (no sorry). Today I fixed the proof script, which had broken from the previous attempt (tactic changes only). The theorem covers only a string `this`. Array.prototype.at was not proven.

## What transferred mechanically vs needed hand work
- mechanical (facts): control flow; let and assignment; the ReturnIfAbrupt idiom; arithmetic and comparisons on math values; the [math] and [number] conversions; literals; calls between translated functions.
- hand work (facts): the whole value and heap model; ESMeta's primitive semantics, e.g. exact floor of a double, +0 vs -0 equality, and the INF values; every callee outside the slice.
- hand work (inference): a full backend would also need records, lists, closures and continuations (generators and async), the ~15 IR ops, nontermination (Lean needs `partial` or fuel, and `partial` blocks proofs), and the spec's 'assert' semantics.
- proof effort (fact): even this 10-line function needed manual case splits on the value type. The tactic proof breaks easily: it broke between Lean runs. Inference: proofs over a full generated spec need a custom simp set or program logic, as SpecTec's Rocq users found (not re-checked here).

## Estimate for a full backend (opinion, low confidence)
- the translator over all ~2,700 spec functions (ESMeta's complete-funcs list): weeks, because the IR is small (Expr.scala has ~39 cases, Inst.scala ~18).
- a faithful runtime and value model in Lean, validated by running test262 through the generated interpreter: 6 to 12 person-months. It needs a JS parser in Lean, or the ESMeta parser exporting ASTs to Lean.
- making it usable for proofs (reasoning principles, fuel, the double-precision float model): unknown. I don't know; this is research, not engineering.

## Has KAIST or EPFL announced one? (see lit/announce.md for the full quotes)
- No public announcement found as of 2026-11-10. Not finding one is not proof that none exists.
- The key quote is from De Santo, Barrière, Pit-Claudel, Warblre, ICFP 2024 (arXiv 2403.11919): "it also does not yet support generation of definitions suitable for use in an interactive theorem prover such as Coq ... add a translator from it to Coq; this could constitute interesting future work".
- EPFL's follow-up Linden (POPL 2026) is a hand-written Rocq embedding with 0 ESMeta mentions. The es-meta GitHub org has no prover exporter, and issue searches for coq, rocq, lean, and isabelle return 0 hits.
- Gap: the earlier search did not use Google Scholar; it used web search and GitHub.

## Files
src/ir2lean.py, src/slice.ir, lean/{Prelude,Gen,Proof,Tests}.lean, lit/announce.md. To rebuild: in lean/, run `lake build Prelude Gen Proof Tests`, then `lake env lean --run Tests.lean`.

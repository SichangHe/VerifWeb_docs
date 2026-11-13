Q1: What does Verus report to an LLM agent per failed proof attempt?
(authored by agents unless marked 🧑)

Bottom line: the participant is partly wrong. Verus names the exact failing clause and source line, not just the function. But it gives no SMT model or counterexample, and localization inside a failing assertion is opt-in and imperfect.

## 1. Per-failure output names the specific clause and line (FACT; refutes "just says which group obligations")
Source: Verus guide, https://github.com/verus-lang/verus/blob/main/source/docs/guide/src/requires_ensures.md
- Precondition at a call site:
  "error: precondition not satisfied / |         x1 < 16, / |         ------- failed precondition / ... /     let n = octuple(20); / |             ^^^^^^^^^^^"
  Marks the exact `requires` conjunct and the call site.
- Assert: "error: assertion failed / |     assert(n == 80); / |            ^^^^^^^ assertion failed"
- Arithmetic: "error: possible arithmetic underflow/overflow / |     let x2 = x1 + x1; / |              ^^^^^^^"
Source: https://github.com/verus-lang/verus/blob/main/source/docs/guide/src/assert_assume.md
- Postcondition: "error: postcondition not satisfied / |           s1.intersect(s2).len() <= s1.len(), / |           ---------------------------------- failed this postcondition"
Source: https://github.com/verus-lang/verus/blob/main/source/vir/src/def.rs (message strings)
- "pub const PRECONDITION_FAILURE: &str = \"precondition not satisfied\";", "POSTCONDITION_FAILURE ... \"postcondition not satisfied\"", "THIS_POST_FAILED ... \"failed this postcondition\"", "THIS_PRE_FAILED ... \"failed precondition\"".
- Also "SPLIT_ASSERT_FAILURE: &str = \"split assertion failure\"".
INFERENCE: the participant's claim is closer to true for the postcondition, if the postcondition is one big `&&` conjunction. Verus points at the whole `ensures` expression, not the sub-clause or the line in the body that breaks it (see 2).

## 2. Finer localization is opt-in: --expand-errors (FACT)
Source: https://github.com/verus-lang/verus/blob/main/source/rust_verify/src/config.rs
- "When the proof fails, try to minimize the failing predicate"
Source: GitHub issues (via search snippets, not read in full): #1220 "Expand-errors blames incorrect conjunct", #1552 "Interaction of `--expand-errors` with `assert(..) by (nonlinear_arith)`", #1214 panic "get_expansion_ctx: did not find the given assert_id". https://github.com/verus-lang/verus/issues/1220
- FACT (secondhand, search summary): in #1552 it always reports all sub-assertions passed under nonlinear_arith. In #1220 it blamed the wrong quantified conjunct.
INFERENCE: this supports "not trivial to expose", in the sense of being buggy and incomplete. Not read in full.

## 3. Multiple errors per function (FACT)
config.rs: "If 0, look for at most one error per function; if > 0, always find first error in function and make extra queries to find more errors (default: 2)"
So by default the agent sees at most about 2 errors per function, not all.

## 4. Timeouts / rlimit give little localization (FACT)
Source: https://github.com/verus-lang/verus/blob/main/source/rust_verify/src/verifier.rs
- "{}: resource limit (rlimit) exceeded" then "; consider rerunning with `--profile` for more details"
config.rs: --profile = "Collect and report prover performance data when resource limits are hit"; --profile-all = "Always collect and report prover performance data".
Guide: https://github.com/verus-lang/verus/blob/main/source/docs/guide/src/profiling.md
- "Sometimes the verification of a Verus function will time out, meaning that the solver couldn't determine whether all of the proof obligations have been satisfied."
So on timeout there is no "which obligation" answer. Quantifier instantiation counts come only via --profile (human-oriented report; whether any LLM paper feeds it back: not found).
Also --time: "To see a more detailed breakdown of where Verus is spending time, you can pass `--time`" (performance.md).

## 5. SMT models / counterexamples (FACT + INFERENCE)
- FACT: internally the model exists but is discarded on the normal path. verifier.rs line ~915: "ValidityResult::Invalid(Some(_air_model), Some(error), assert_id_opt)" (leading underscore = unused). AIR uses it to continue checking for more errors (air/src/context.rs: "FoundInvalid(Vec<AssertionInfo>, Option<Model>)", "check_valid_again") and exposes "Evaluate a boolean AIR expression in the current solver model." (`evaluate_bool`), plausibly what expand-errors uses (INFERENCE).
- FACT: I found no CLI flag to print a counterexample (grep of config.rs options: log, expand-errors, multiple-errors, profile; none for models).
- ProofPlumber paper (CAV 2024) via search summary (not read in full): SMT solvers "often do not produce a useful concrete model" when they return unknown, "the common case when a Verus or Dafny proof fails." https://link.springer.com/chapter/10.1007/978-3-031-65627-9_17
- So "not trivial to expose" is plausible for models (quantified, unknown results). INFERENCE.
- --log options exist (config.rs: "Log SMT queries", "Log complete SMT transcript", "Log automatically chosen triggers") but are dev debugging dumps.

## 6. What LLM systems actually feed back
AutoVerus (Yang et al., OOPSLA 2025), https://arxiv.org/abs/2409.13082
- "In each iteration, AutoVerus collects all the verification errors E in 𝑃𝐵 from Verus (Line 5), picks one error 𝐸 from E to fix next (Line 6), and prompts a repair agent that suits 𝐸 (Line 7)."
- "The prompt to agent 𝐴𝑡 that handles a verification error of type 𝑡 includes not only the Verus program under repair, but also 1) the code snippet and detailed information about an error 𝐸𝑡 to be fixed, which has the verification-error type 𝑡, and 2) the instruction about how to fix errors of type 𝑡."
- Types: "loop invariant not satisfied before/at end of loop", "assertion errors", "arithmetic under/overflow errors", "type mismatch (syntax) errors", plus precondition/postcondition (per its Figure 6, only partly read), and a "repair_default".
- Priority: "once Verus identifies a bound error for any component of an expression 𝐸, it will make no further attempt to prove any property that involves 𝐸."
- Ablation: a generic agent given "the whole Verus error report" solved "17 out of 37 tasks", vs AutoVerus's own per-type design solving all 37 (these tasks are the 37 AutoVerus fixed in debugging). Evidence that the error-type classification and targeted prompts add value over raw output.
- Related: "DafnyBench adds the whole error message into the prompt".
- Not checked (time): AlphaVerus, SAFE, VeruSAGE, Verus-bench, RagVerus, VeriStruct (appeared in search, arXiv 2510.25015). Their feedback formats are unverified.
Verus guide, official recommendation (llmforverusproof.md): "Provide a Verus binary for the model to run and see error messages" and "Keep editing your proof until Verus shows no errors." So the modern agent loop sees raw rustc-style Verus output (message, spans, labels, the above), nothing more by default.

## Verdict
- "Not really pre/postcondition, just says which group obligations": REFUTED in part. Verus gives the specific failed `requires`/`ensures` clause plus the call/assert span (section 1). Correct in part for large conjunctive asserts/postconditions: no sub-clause blame unless --expand-errors, and that is buggy.
- "Doesn't tell you anything about whether something went wrong in this particular function": REFUTED for ordinary failures (errors are span-located inside the function). TRUE for timeouts (no obligation named) and for the "why" (no model, no failing path).
- "Not trivial to expose that stuff": SUPPORTED (inference) by open expand-errors bugs and by the unused `_air_model`.

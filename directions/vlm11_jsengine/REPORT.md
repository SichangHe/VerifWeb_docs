# Is a formally verified JS engine doable now with agents?
(authored by agents unless marked 🧑)

Answer (opinion, from the evidence below): a whole verified engine is not doable now; a verified slice of a real engine is.

## Why a whole engine is out of reach

- engine size (fact, measured with tokei; [sizes.md](sizes.md))
  - Boa ~167k lines of Rust (engine 106k, builtins 51k), test262 94%
  - Nova ~117k lines of Rust, test262 ~80%
  - QuickJS ~77k lines of core C; engine262 ~54k lines of TypeScript
  - Lightpanda embeds V8; its binding layer is ~10k lines of Zig
- largest verified systems are ~10–30x smaller (fact, quotes in sizes.md)
  - Verus SOSP'24 systems: 6.1k code / 31k proof; Atmosphere 6k code, <2.5 person-years
  - seL4: 8.7k lines of C, 200k proof, ~20 person-years; IronFleet 3.6:1, 3.7 person-years
- extrapolation (inference): 60–170k lines of code × 3–13 proof per code line ≈ 300k–800k proof lines
- agent record (fact): the largest known agent proof is ~7.8k lines of Rocq from a human template; no agent-built repo-scale verified system was found
- prior JS formal work covers the spec, not engines (fact): JSCert (ES5, Coq), KJS, JISET/ESMeta; verified pieces are regex (Warblre, Linden) and one JIT pass (VeRA); no verified full JS engine or JIT exists

## What blocks it

- f64 (fact, hit in our attempt): Verus has no usable float semantics, and JS numbers are f64
- GC and unsafe heap (inference): earlier local GC proofs were models, not upstream code (cx_proofs audit)
- spec size (fact): ECMA-262 2025 is 847 pages; ES10 had 2,026 algorithms and 10,101 steps
- JIT (inference): needs semantics for generated machine code; Boa and Nova are interpreters, so a JIT can be skipped

## Our throughput and quality (local evidence; [throughput.md](throughput.md))

- 51 passing distinct Verus proofs: ~6.6k executable + ~3.5k spec/proof lines (fact)
- 41% of them have a caveat: 15 overstated, 6 unsound (fact, from the audit)
- all sampled proofs were on hand-written models, not upstream source (inference from 5 headers)
- rate ≈ 500 clean executable lines per agent-hour (estimate; agent-hours are unreliable, bracket 100–1400)
- at that rate, 300k+ proof lines is not just effort: the 41% caveat rate means human spec review is the bottleneck (opinion)

## Real attempt on Boa ([attempt/ATTEMPT.md](attempt/ATTEMPT.md))

- verified Boa's `f64_to_int32` against ECMA-262 ToInt32 for all 2^64 inputs (fact; I re-ran it: "40 verified, 0 errors", no `external_body`/`assume`)
  - non-vacuity: 3 mutants fail, the `assert(false)` probe fails, sanity checks on edge values pass
- changes to upstream: input passed as u64 bits because of f64; the ~5-line fast path was dropped; helpers hoisted
- effort: ~6 minutes and ~30 verifier runs for ~68 upstream lines (fact as reported by the subagent; the time looks short, so treat it as a lower bound)
- the engine crate has ~43 similar conversion functions (grep count)
- takeaway: pure, loop-free leaf functions are cheap; this says nothing about the interpreter, object model, or GC

## A bite-sized thesis (opinion)

- "verified spec-conformant core of a Rust JS engine"
  - scope: numeric conversions + one builtin family (e.g. Array index/length clamping, String) + the lexer, on real Boa/Nova source
  - specs generated from ECMA-262 pseudocode (via ESMeta), which addresses the spec-review bottleneck
  - needed contribution: an f64 model for Verus that matches IEEE-754 binary64
  - web angle: the same verified core could serve a lightweight agent browser (Lightpanda currently uses V8)
- risk: reviewers may see it as "verified builtins", not a verified engine; the human must judge novelty

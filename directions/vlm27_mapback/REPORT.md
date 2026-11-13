# vlm27_mapback: verify a Rust JS engine, then "map back" to V8?
(authored by agents unless marked 🧑)

Labels: [F] fact with quote+URL, [S] quote from a Google Scholar result snippet (truncated by Scholar, recheck before citing), [I] inference, [O] opinion. Raw search output: `scholar/q1..q6.txt`, `pages/`. Reading only; nothing run, nothing published.

## Short answer
- [O] the framing is sound only if "map back" produces a concrete artifact that runs against V8 (tests, an oracle, a checked algorithm merged upstream). "Our Rust engine is verified, and V8 implements the same spec" will be read as a toy result
- [O] strongest version: verify one spec area end to end in the Rust engine (e.g. regex, number/string builtins, Array builtins), then use the verified code as (1) an exact oracle for differential testing of V8/SpiderMonkey/JSC, and (2) a source of algorithms/invariants upstreamed into V8. The regex line of work (Barrière, Pit-Claudel, EPFL) already did exactly this and got code merged into V8; it is the template and the closest competitor
- [O] what stops "toy": bugs or merged patches in V8/SpiderMonkey/JSC; a verified component that V8 actually adopts; or a JIT-side check (translation validation) that runs on TurboFan output. Bugs in Boa alone will not count, matching the human's own point
- [I] a fully verified whole engine against ECMA-262 does not exist; the biggest prior attempts are reference interpreters (JSCert/JSRef, KJS, ECMA-SL/ECMARef), not fast engines. Nothing found that verifies a Rust JS engine

## Evidence

1. prior work that maps a spec/reference back to big engines
- ESMeta family (KAIST, Ryu): mechanized spec → conformance tests run on real engines
  - [S] "detected 44 bugs in four engines (V8, GraalJS, QuickJS, …" — Ryu & Park, "JavaScript Language Design and Implementation in Tandem", CACM 2024 (https://dl.acm.org/doi/10.1145/3624723)
  - [S] "We extend JEST, the state-of-the-art JavaScript conformance test synthesizer … We detected a bug in SpiderMonkey that breaks the logic of …" — Park et al., "Feature-sensitive coverage for conformance testing", OOPSLA 2023 (Scholar q1/q2)
  - [I] their "map back" = generated JS programs + expected results from the spec, run on each engine. No proof is transferred
- regex verification (EPFL): closest to the human's idea
  - [F] "we discover several cases where state-of-the-art algorithms were either wrong (semantically incorrect), inefficient … We introduce novel algorithms to restore correctness and linear complexity … some have also been merged in the V8 JavaScript implementation used in Chrome" — Barrière & Pit-Claudel, "Linear Matching of JavaScript Regular Expressions", PLDI 2024 (https://arxiv.org/abs/2311.17620)
  - [F] "the first mechanized, succinct, practical, complete, and proven-faithful semantics … proving it equivalent to a preexisting line-by-line embedding of the official ECMAScript specification … the first formal proof of the PikeVM algorithm used in many real-world engines" — Barrière, Deng, Pit-Claudel, POPL 2026 (https://arxiv.org/abs/2507.13091)
  - [S] Warblre: "we conjecture and formally verify a fundamental invariant of the ECMAScript regex … We show that the JavaScript engine can execute the Test262 official ECMAScript …" — De Santo, Barrière, Pit-Claudel, ICFP 2024 (Scholar q5)
  - [I] map-back mechanism here: proof finds the algorithm bug → fixed algorithm upstreamed to V8 by hand. Not a proof about V8's C++
- JIT translation validation on V8
  - [S] "(TV) that checks whether a specific compilation is semantically … TurboFan (JIT compiler of V8) as SMT encoding. For efficient validation, we design a staged strategy for JS JIT compilers" — Kwon et al., TurboTV, ISSTA 2024 (Scholar q3)
  - [S] "Optimuzz can effectively find miscompilation bugs in TurboFan … We employed TurboTV for translat…" — Kwon et al., POPL 2025 (Scholar q3)
- differential testing with oracles
  - [S] JIT-Picker: "oracle does not scale and only alerts to bugs breaking explicitly encoded invariants … [38, 40] rely on the language specification to derive test cases" — Bernhard et al., CCS 2022 (Scholar q4)
  - [I] differential testing between engines has no ground truth when all disagree; a verified reference would be that ground truth. JEST already uses the (unverified) mechanized spec this way
- Icarus (SpiderMonkey inline-cache stubs verified then emitted as C++), see vlm14_engine/REPORT.md; this is the "verify then port into the C++ engine" path, and it is the only one found that ships proved code into a big engine

2. how "map back" could work [O unless labeled]
- a. verified Rust builtin as a test oracle: generate inputs (e.g. edge numerics like `at(-1e300)` from poke_esmeta) and compare V8 output. Transfers: builtins, numerics, regex, string ops. Cheap
- b. proof finds algorithm-level bug → hand-port fix to V8 (regex precedent). Transfers: any algorithm the spec fixes semantically
- c. verified invariant → runtime assertion / CBMC/ESBMC harness on the C++ function. [I] feasible only for small leaf functions; no verified C++ of engine size found (vlm14)
- d. JIT: Rust interpreter doesn't help; TurboTV-style translation validation is the existing route. A verified Rust reference could be TurboTV's semantics source [I], nothing found doing that
- does not transfer: GC (V8's Oilpan/Orinoco design differs from any Rust engine; a proof about Boa's GC says nothing about V8's), inline caches, hidden classes, JIT speculation/deopt. These are where V8's security bugs are [I]

3. "fully verified JS engine against the standard"
- [I, from prior knowledge, not re-searched] JSCert/JSRef (Coq, ES5, POPL 2014), KJS (K framework, ES5), JaVerT (JS verification, not engine). All target ES5 and are slow reference interpreters
- [S] recent: "ECMA-SL: a platform for specifying and running the ecmascript standard", "ECMARef6: A Reference Interpreter for Modern JavaScript" (Scholar q5); reference interpreters, not proved
- ESMeta: mechanized from the spec text, executable, not a proof; it type-checks the spec (JSTAR)
- nothing found: a verified Rust JS engine, or any verified engine for ES2015+
- what Rust adds [O]: memory-safe baseline, Verus/Aeneas tooling (poke_esmeta proved 2 Boa builtins in ~1 h and found a real crash). It does not make V8 claims stronger by itself

## Not found
- any work that formally relates a verified engine's proof to V8/SpiderMonkey C++ code (beyond Icarus generating it)
- verified Rust reference used as a differential-testing oracle for JS engines
- Scholar results for "Rust verified reference + C++ differential testing" were only C→Rust translation papers (q6)

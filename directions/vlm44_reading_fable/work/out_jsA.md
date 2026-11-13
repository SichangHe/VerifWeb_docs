(authored by agents unless marked 🧑)

Group jsA: formal JavaScript semantics. Order is by priority, not by id.

Summary for the feasibility question. Full-language formal JS semantics stop at ES5 (2009) or ES6 (2015); the Ecma standard has shipped yearly since 2015. The only parts proven in a theorem prover against a recent edition are regular expressions (ES2023, Rocq). The one line that tracks the yearly standard automatically is ESMeta (paper 48), which is a tool for type checking and testing the prose spec, not a proof framework. No paper here proves anything about a real engine's code (Boa, V8, etc.); proofs are about models, and engines are only used as test oracles.

---
37 A Trusted Mechanised JavaScript Specification, Martin Bodin, Arthur Charguéraud, Daniele Filaretti, Philippa Gardner, Sergio Maffeis, Daiva Naudžiūnienė, Alan Schmitt, Gareth Smith, POPL, 2014
SHOWS: JSCert is a rule-by-rule model of the core of ES5 written in Coq (a proof assistant); JSRef is an interpreter extracted from Coq to OCaml and proved correct against JSCert in Coq, and run on test262. The proof is about a model and an interpreter, not a real engine. Coverage is partial (no for-in, no parser, partial libraries).
QUOTE: "we pass 1796 tests; the others fail due to for-in, calls to libraries we have not specified, or the parser." (Section 1, of 2782 core-language tests)
WHY: It is the baseline "trusted spec in a prover" and it shows the cost and the gaps: ES5 only, incomplete, ~8 people for a year (that figure is quoted from paper 54, footnote 11), and no update after 2014 is described in the text.
PRIORITY: high - the baseline everyone compares against
READ: abstract, introduction, test262 paragraph, scope discussion; not the Coq rule sections.

---
54 KJS- A Complete Formal Semantics of JavaScript, Daejun Park, Andrei Ştefănescu, Grigore Roşu, PLDI, 2015
SHOWS: KJS is an executable ES5.1 semantics in the K framework (a rule-based language-definition tool) that passes all 2,782 core-language test262 tests, was used to find bugs in V8, WebKit, SpiderMonkey, and to verify small programs (BST/AVL-style functions, one known security bug found) by symbolic execution. Proofs/verification are on JS programs under the model, not on an engine.
QUOTE: "KJS has been tested against the ECMAScript 5.1 conformance test suite, and passes all 2,782 core language tests." (Abstract)
WHY: It is the strongest evidence that a complete ES5 semantics plus a free program verifier is feasible in a K-style tool with about one person-week per verified example; it says nothing about ES6+ and the paper states no plan to track new editions beyond "future work".
PRIORITY: high - complete semantics plus verifier, ES5
READ: abstract, introduction, section 4 (evaluation), 5.2-5.4, related work comparison.

---
33 A Coq Mechanization of JavaScript Regular Expression Semantics, Noé De Santo, Aurèle Barrière, Clément Pit-Claudel, ICFP, 2024
SHOWS: Warblre, a line-by-line Coq (Rocq) translation of the regex chapter (22.2) of the latest ECMA-262 edition (2023); proved that matching terminates and never hits an assertion failure; extracted to OCaml/JS and run on test262 and differential fuzzing against V8's Irregexp (no disagreement found). The proofs are on the model; it also verifies one optimization taken from Irregexp.
QUOTE: "We pass 495 out of 498; the remaining 3 tests time out." (Section 6.2, core regex-matching tests in test262)
WHY: The best example of a spec mechanization that follows the current standard and claims updates cost about as much as the spec change (Section 6.3, shown on a simulated feature addition), but it covers only regexes, not the language.
PRIORITY: high - only recent-edition prover mechanization
READ: abstract, introduction, section 3 start, section 6 (testing, update case study), conclusion pointers.

---
48 JavaScript Language Design and Implementation in Tandem, Sukyoung Ryu, Jihyeok Park, CACM, 2024
SHOWS: ESMeta extracts an executable specification from the prose ECMA-262 text each year and is part of the ECMA-262 and Test262 continuous integration; related tools JEST (generates tests, found 44 engine bugs and 27 spec bugs in ES2020), JSTAR (93 type-related spec bugs). This is type checking and testing, not theorem proving, and no engine code is proved.
QUOTE: "We detected 44 bugs in the engines and 27 bugs in ES2020." (section on JEST)
WHY: It is the only work in this group that keeps up with the yearly standard (in CI since Nov 2022), so it answers "how to stay current" but gives no proofs.
PRIORITY: high - only up-to-date approach; short read
READ: whole article skimmed (three-column text is garbled); exact test262 pass numbers for ESMeta not found in this text.

---
45 Formal Verification for JavaScript Regular Expressions- A Proven Mechanized Semantics and Its Applications (Extended Version), Aurèle Barrière, Victor Deng, Clément Pit-Claudel, POPL, 2026
SHOWS: A shorter, easier-to-reason-about backtracking-tree semantics of ECMAScript 2023 regexes in Rocq (over 15k lines), proved equivalent to Warblre (paper 33), used to prove or disprove regex rewrites (finding bugs in the regexp-tree tool) and to give the first formal proof of the PikeVM algorithm (a regex-matching algorithm used in real engines; the proof is about the algorithm, not an engine's code).
QUOTE: "We ensure its faithfulness by proving it equivalent to a preexisting line-by-line embedding of the official ECMAScript specification of JavaScript regular expressions." (Abstract)
WHY: Shows the second layer you would need: a spec-faithful model plus a proof-friendly model with an equivalence proof; still ES2023 regex only.
PRIORITY: medium - extends 33, regex only
READ: abstract, introduction, section 4 start, related work, applications overview.

---
58 On the computational complexity of JavaScript regex matching, in Rocq, Victor Deng, Aurèle Barrière, Clément Pit-Claudel, arXiv, 2026
SHOWS: Rocq proofs, on the Warblre/ES2023 regex model, that JS regex matching with expanded lower-bounded quantifiers is PSPACE-complete (meaning: believed to need exponential time in the worst case) and that regex parsing without lookarounds is OptP-complete; some steps are not mechanized (stated in the text).
QUOTE: "JavaScript regex matching with expanded lower-bounded quantifiers is PSPACE-complete." (Abstract)
WHY: Useful only as evidence that the regex model is reusable; the authors say porting to ES2025 "is left to future work", a concrete sign that updates lag.
PRIORITY: low - theory result, off our path
READ: abstract, introduction, related work, "Other regex languages" and limitations section.

---
49 JaVerT 2.0- Compositional Symbolic Execution for JavaScript, José Fragoso Santos, Petar Maksimović, Gabriela Sampaio, Philippa Gardner, POPL, 2019
SHOWS: A symbolic execution tool (runs code on unknown inputs to explore paths) for JS, built on an ES5 Strict-to-JSIL compiler (custom goto language) with soundness proofs in the paper (pen-and-paper, not a prover); tested on data-structure libraries and found a new bug in Buckets.js.
QUOTE: "JS-2-JSIL has full support for the entire core of ES5 Strict, as well as most of the associated built-in libraries. We do not implement the Date, RegExp, and JSON libraries" (Section 6)
WHY: Shows program-level analysis of real npm code works on ES5 Strict with line-by-line compiler checked by test262 (8797 applicable tests, per paper 43), and that ES6 would need "additional constructs", i.e. the semantics falls behind.
PRIORITY: medium - program analysis, ES5 only
READ: abstract, introduction, section 3.1, section 6 coverage paragraph, conclusion.

---
46 Gillian, Part I- A Multi-language Platform for Symbolic Execution, José Fragoso Santos, Petar Maksimović, Sacha-Élie Ayoun, Philippa Gardner, PLDI, 2020
SHOWS: Gillian, a platform parametric in a memory model, with a proved-sound symbolic engine (parametric soundness proof in the paper); instances for JS (ES5 Strict, reusing the JaVerT compiler) and C; found bugs in Buckets.js and Collections-C.
QUOTE: "identifying 9013 and passing 9005 tests. The failing tests are all due to a discrepancy between how Unicode characters are treated in JavaScript ... and OCaml" (Section 3.3/4, test262 for ES5 Strict)
WHY: Shows the JS side is stuck at ES5 Strict but the platform is language-agnostic, so a newer JS front end could reuse it; Gillian-JS compiler is 7694 lines of OCaml.
PRIORITY: medium - reusable infrastructure, JS still ES5
READ: abstract, introduction, section 3.3 and 4 (JS case study), conclusion.

---
36 A Trusted Infrastructure for Symbolic Analysis of Event-based Web APIs, Gabriela Cunha Sampaio, Imperial College London PhD thesis, 2022
SHOWS: JaVerT.Click: reference implementations (written in JS, run on JaVerT 2.0) of DOM Core Level 1, DOM Events, Promises, async/await, WebMessaging and WebWorkers; tested against their official test suites (DOM Events: 100% of the 56 appropriate tests), which exposed gaps and bugs in test suites, plus symbolic testing of three libraries that found six bugs. Analysis is of JS programs on a model; no engine code is verified. Language level is ES5 strict plus a transpiler for some ES6+ features.
QUOTE: "By testing the symbolic execution engine against three open-source libraries, we established the bounded correctness of functional properties and found real bugs." (Abstract)
WHY: The closest example of formalizing DOM/web APIs next to a JS semantics, but only events and messaging, built by hand against the standard, and limited to ES5.
PRIORITY: high - only web API/DOM work here
READ: abstract, chapter 1, 6 (summary), parts of 7.1 and 8; not chapters 2-5 in detail.

---
43 ECMA-SL - A Platform for Specifying and Running the ECMAScript Standard, Luís Miguel Alves Loureiro, IST MSc thesis, 2021
SHOWS: ECMA-SL, a custom intermediate language, and ECMARef5, an ES5.1 reference interpreter written in it that follows the standard line by line; passes 12,026 of 12,068 applicable test262 tests; ECMA-SL2English regenerates HTML of the standard text from the code (above 80% similarity). No proofs.
QUOTE: "ECMARef5 passes 12,026 tests out of 12,068 applicable tests, while JSCert passes 1,796 tests, KJS passes 2,782 tests, S5 passes 8,157 tests, and JS-2-JSIL passes 8,797 tests." (Section 3, related work)
WHY: Gives the best ES5 test262 count and a comparison table of earlier semantics; no verification, and the thesis lists adapting to newer versions as long-term future work.
PRIORITY: medium - comparison table is useful
READ: abstract, intro, related work, conclusion; not implementation chapters. Note: it reports JISET at 62.4% of ES10 tests, while paper 47 says JISET passed all 18,064 applicable tests; the two sources disagree.

---
38 A Typed Intermediate Language for Specifying the ECMAScript Standard, André Filipe Ferreira do Nascimento, IST MSc thesis, 2023
SHOWS: Typed ECMA-SL: adds static types to ECMA-SL; type safety proved for a formal subset (on paper); the type system found bugs (unknown variables, wrong argument counts) in ECMARef5/6. ECMARef6 itself was not typed here.
QUOTE: "the last ES version supported by the ECMA-SL project is the 6th (ES6), released in 2015." (Chapter 1)
WHY: Direct statement from the ECMA-SL team that keeping a hand-written reference interpreter up to date with yearly editions is the open problem; the standard was at its 14th edition then.
PRIORITY: low - tooling for maintaining a model
READ: abstract, introduction contributions, conclusion; not the type system chapters.

---
47 Implementation-Based Generation of the ECMAScript Standard, Patrícia Alexandra Ferreira Pereira, IST MSc thesis, 2024
SHOWS: ECMA-to-HTML generates the HTML of the standard (ES13) from ECMARef6 with annotations; structural similarity to the official text averages 88.3%. No proofs. It also reports ECMARef6 passes 92% of 20,655 ES6 test262 tests.
QUOTE: "ECMARef5 passed 99,6% and ECMARef6 passed 92%, respectively" (Section 2.2, ECMA-SL evaluation, on 12,068 ES5 and 20,655 ES6 tests)
WHY: Confirms that the ECMA-SL line reached ES6 at 92% and is still working on rendering the ES13 text; no engine-level result. Its related-work table appears to have errors (for example JaVerT labelled ES6), so do not copy numbers from that table.
PRIORITY: low - same line as 43 and 38
READ: abstract, section 2.2, related work table, conclusion; not the architecture or user study.

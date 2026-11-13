# Group jsB reading notes
(authored by agents unless marked 🧑)

Short terms used below. "Mechanized" = written in a tool (proof assistant or executable code) so a computer can run or check it. "Test262" = the official ECMAScript conformance test suite. "Translation validation" = after one compile, use a solver to check that this compiled output means the same as the input.

Overall picture from this group: for the JS standard itself, the Korean KAIST line (JISET, JEST, JSTAR) is the only one that is automatic and tracks new ECMAScript versions, but it is test/analysis based, not proofs. For DOM, the only machine-checked model is the 2018 Isabelle one; it is old and small. For Wasm, a proved and test-passing Coq model exists and is kept current. For JIT, Icarus gives a proof but for a reimplemented subset of Firefox; TurboTV and Optimuzz are testing-plus-solver tools.

---

## 50  JEST- N+1-version Differential Testing of Both JavaScript Engines and Specification, Jihyeok Park, Seungmin An, Dongjun Youn, Gyeongwon Kim, Sukyoung Ryu, ICSE, 2021
- SHOWS: It auto-generates small JS test programs from a mechanized ES11 (a model extracted from the standard's text) and runs them on 4 engines (V8, GraalJS, QuickJS, Moddable XS); a disagreement between engines, or between engines and the model, points to a bug in an engine or in the standard. Testing only, no proof.
- QUOTE: "it detected 44 engine bugs in four different engines and 27 specification bugs in ES11." (Abstract)
- WHY: Shows the standard text itself has bugs and that a mechanized spec can be an oracle (reference answer) for engine testing; relevant if we test Boa against a formal model. Breakdown: 16 GraalJS, 6 QuickJS, 20 Moddable XS, 2 V8; 1,700 programs covering 97.78% of syntax and 87.70% of semantics (Abstract, Sec. on results). The paper says all were confirmed by TC39 and engine teams.
- PRIORITY: high - closest to our test-oracle idea
- READ: Abstract, introduction, evaluation (coverage, bug tables), conclusion (about 40% of the text).

## 51  JISET- JavaScript IR-based Semantics Extraction Toolchain, Jihyeok Park, Jihee Park, Seungmin An, Sukyoung Ryu, ASE, 2020
- SHOWS: A tool that reads the ECMAScript text and automatically builds a parser and a translator into an intermediate language, giving an executable JS semantics for ES7 to ES10; checked by running Test262, not proved.
- QUOTE: "the extracted core semantics of the latest ECMAScript (ES10, 2019) passed all 18,064 applicable tests." (Abstract)
- WHY: It is the answer to "can a formal JS semantics follow the yearly standard updates": 95.03% of algorithm steps compile automatically, but only after about 277 steps (137 core, 140 built-in library) were completed by hand, and tests for non-strict mode, modules, early errors and many built-ins (17,926 of 35,990 tests) were excluded (Sec. 6, Table 4). Failures (1,709) exposed 9 spec errors, 4 new, all confirmed by TC39.
- PRIORITY: high - base for a JS semantics
- READ: Abstract, introduction, evaluation section with Test262 table, conclusion.

## 52  JSTAR- JavaScript Specification Type Analyzer using Refinement, Jihyeok Park, Seungmin An, Wonho Shin, Yusung Sim, Sukyoung Ryu, ASE, 2021
- SHOWS: A static type analysis over the JISET-extracted ECMAScript algorithms that finds type-related mistakes in the standard text; run on all 864 spec versions from 2018 to 2021. Analysis, not proof, and it checks the spec, not engines.
- QUOTE: "detected 157 type-related specification bugs with 59.2% precision; 93 out of 157 bugs are true bugs. Among them, 14 bugs are newly detected by JSTAR, and the committee confirmed them all." (Abstract)
- WHY: Shows the mechanized spec can be kept up to date and checked on every commit (137.3 s per version), but 40% of reports are false alarms and it depends on JISET's extraction; it tells us the standard text is a shaky foundation by itself.
- PRIORITY: medium - spec bugs, not engine verification
- READ: Abstract, introduction, bug-category and evaluation parts (text layout was garbled; conclusion not located).

## 34  A Formal Semantics of the Core DOM in Isabelle-HOL, Achim D. Brucker, Michael Herzberg, WWW Companion, 2018
- SHOWS: A mechanized model of the DOM node tree in Isabelle/HOL (a proof assistant), with proofs that the main DOM operations are functionally correct and keep the tree well-formed; it is executable, so the DOM compliance test suite can be run on the model. A proof about a model, not about browser code.
- QUOTE: "We use the formalization to verify the functional correctness of the most important functions defined in the DOM standard." (Abstract)
- WHY: The only machine-checked DOM model in this group; short paper, covers the node tree only (shadow-root fields appear in the model but events and HTML are future work), and its own conclusion says linking it to real browser code is the most important future work, so that gap is open for us. Its Isabelle AFP entry is named Core_DOM.
- PRIORITY: high - only proved DOM model
- READ: Abstract, introduction, data-model overview, conclusion/future work; skimmed proof section. I did not read the test-suite numbers closely.

## 44  Featherweight Firefox- Formalizing the Core of a Web Browser, Aaron Bohannon, Benjamin C. Pierce, WebApps, 2010
- SHOWS: A paper-and-OCaml model of a browser's core (windows, DOM trees, cookies, HTTP, user input, small scripting language) as small-step rules (step-by-step execution rules). No proofs and no tests against real browsers; the authors want it as a base for later security proofs.
- QUOTE: "No security enforcement mechanisms are included—instead, the model is intended to serve as a basis for formalizing and experimenting with different security policies and mechanisms." (Abstract)
- WHY: Shows what a browser-level model has to include (asynchrony, multiple windows, event loop) but it is from 2010, uses a toy script language instead of real JS, and is unvalidated, so it is a design reference only.
- PRIORITY: low - old, unvalidated toy model
- READ: Abstract, introduction, related work and future work (sections 1, 7, 8); skimmed model.

## 57  Local Hoare Reasoning about DOM, Philippa A. Gardner, Gareth D. Smith, Mark J. Wheelhouse, PODS, 2008
- SHOWS: A Hoare-style logic (Context Logic, a cousin of separation logic) for a small part of DOM Core Level 1 tree updates, with complete reasoning for straight-line code and an example proving an invariant of a small JS-like program. Pencil-and-paper proofs, no tool.
- QUOTE: "We have however already found holes in the DOM specification: for example, DOM does not specify how the normalize method of the Element class interacts with pointers in the store." (Sec. 6, Conclusion)
- WHY: The oldest DOM specification effort; shows the DOM standard in English is incomplete and not compositional, but it covers only tree and text nodes (no attributes, fragments), has no prototype tool, and predates modern DOM, so it is background, not a base.
- PRIORITY: low - 2008, paper-only, small subset
- READ: Abstract, introduction, conclusion; skimmed the rest.

## 66  Utilising and Scaling the WebAssembly Semantics (Dagstuhl Seminar 25241), Amal Ahmed, Andreas Rossberg, Deian Stefan, Conrad Watt, Michelle Thalakottur, Dagstuhl Reports, 2025
- SHOWS: A 2025 seminar report (talk abstracts and working-group notes, no new results of its own) on the state of Wasm formal semantics: the official spec has a machine-checked formal semantics, the SpecTec tool is adopted to author the spec, and open topics are verified compilation, spec-tool maintenance, GC, concurrency and JS interop.
- QUOTE: "The extracted runtime now passes the Wasm 2.0 core test suite fully." (Sec. 3.11, Rao talk on WasmCert-Rocq)
- WHY: A cheap map of who is doing what in Wasm verification; also names the main maintenance risk ("the risk is that either the formal specification gets in the way of evolving the language, or that the formalization falls behind", Sec. 1), and shows Wasm-to-native verification (Cranelift) and test generation from the spec (WEST) exist. The group agreed spec test coverage for GC "should be improved" (Sec. 4.2).
- PRIORITY: medium - good map, few details
- READ: Whole report (about 18 pages).

## 42  Designing and Maintaining an Efficient WebAssembly Mechanisation, Xiaojia Rao, Imperial College London PhD thesis, 2025
- SHOWS: A thesis on WasmCert-Coq, a Coq mechanization of Wasm updated from 1.0 to 2.0, with a verified-by-construction interpreter that passes the official Wasm test suite, and Iris-Wasm, a program logic (separation-logic based) for proving Wasm programs including host interaction. Proofs about the model, extracted to a runnable interpreter.
- QUOTE: "Unless stated otherwise, all of the works throughout this thesis have been fully mechanised in Coq." (Sec. 1)
- WHY: The best example of a proved, tested, and kept-up-to-date formal semantics of a web-related language; its mechanization also found errors in the Wasm spec (Sec. 3.10.3). It also states the cost: keeping up with the spec "remains a demanding task" and risks falling behind, which is why it points to SpecTec as the fix (Conclusion). Passes all tests except it notes SIMD tests were handled separately (Sec. 3.11.3, not read in detail).
- PRIORITY: high - model for what feasible looks like
- READ: Abstract, Chapter 1 (contributions), Conclusion and Future Work, and skimmed Sec. 3.10 and 3.11 headings; chapters 2 to 5 body not read (thesis is 577 KB).

## 59  Optimization-Directed Compiler Fuzzing for Continuous Translation Validation, Jaeseong Kwon, Bongjun Jang, Juneyoung Lee, Kihong Heo, PLDI, 2025
- SHOWS: Optimuzz, a fuzzer that steers input generation toward a chosen compiler optimization and then checks each compile with a translation-validation tool (Alive2 for LLVM, TurboTV for TurboFan), run on LLVM and on V8's TurboFan JIT. Testing plus per-compile solver checks, not a proof of the compiler.
- QUOTE: "We also applied Optimuzz to the latest version of LLVM and discovered 55 new miscompilation bugs." (Abstract)
- WHY: For the JS JIT it only reproduced 4 known TurboFan bugs faster than the baseline Fuzzilli (6-hour limit), and found no new TurboFan bugs; the new bugs are in LLVM, so evidence for JS JITs is weak. It depends on how much of the compiler the validator can encode.
- PRIORITY: low - JIT part is thin
- READ: Abstract, introduction, implementation and TurboFan evaluation, discussion, conclusion.

## 40  Bullseye- Detecting Prototype Pollution in NPM Packages with Proof of Concept Exploits, Tariq Houis, Shaoqi Jiang, Mohammad Mannan, Amr Youssef, NDSS, 2026
- SHOWS: A dynamic analysis (runs the code) that runs npm packages' own tests with attack inputs and checks whether Object.prototype got polluted; run on 44,513 popular packages and 5,879 others. It finds real bugs in Node.js libraries, not in JS engines or the standard; no formal model, no proof.
- QUOTE: "We detected zero-day prototype pollution vulnerabilities in 290 packages, with no false positives." (Abstract)
- WHY: Shows JS-level security checking at scale (149 CVEs assigned as of July 2025), but it sits above the engine, so it only matters to us as a user of the prototype semantics, not for engine or JIT verification.
- PRIORITY: low - npm library bugs, off target
- READ: Abstract and introduction only; evaluation and conclusion headings not located, not read.

## 78  Icarus- Trustworthy Just-In-Time Compilers with Symbolic Meta-Execution, Naomi Smith, Abhishek Sharma, John Renner, David Thien, et al., Ranjit Jhala, Deian Stefan, SOSP, 2024
- SHOWS: A framework (about 20K lines of Rust) where inline-cache stub generators of a JIT are written in a DSL and checked by an SMT solver (via Boogie/Corral) so that all stubs the JIT could ever generate are safe; they reimplemented parts of Firefox's SpiderMonkey CacheIR and exported C++ with no measured slowdown. A solver proof of the reimplemented subset, with trusted parts (the Icarus toolchain, the low-level MASM interpreter, hand-written contracts).
- QUOTE: "verifying the JIT implementation statically ensures the security of all possible programs that the JIT could ever generate at run-time" (Abstract)
- WHY: The strongest JIT result here: it caught all 6 reproduced real Firefox CacheIR bugs in under 30 seconds each and verified the fixes in under a minute (Sec. 4.3), but it covers a subset (a few of 270 generators across 21 operations) and needs code rewritten in its DSL; it does not touch a Rust engine or a full JS semantics.
- PRIORITY: high - proof-level JIT verification exists
- READ: Abstract, introduction, Sec. 4.3 evaluation, Sec. 5 limitations.

## 85  Translation Validation for JIT Compiler in the V8 JavaScript Engine, Seungwan Kwon, Jaeseong Kwon, Wooseok Kang, Juneyoung Lee, Kihong Heo, ICSE, 2024
- SHOWS: TurboTV, an SMT-based checker (12K lines of OCaml) that encodes the semantics of V8's TurboFan IR (not full JS) and checks individual compilations for correctness; it encodes 306 of 914 TurboFan operators in V8 11.7.2. Per-compile checking of real compiler output, not a proof of the compiler.
- QUOTE: "TurboTV effectively validated a large number of compilations of TurboFan with a low false positive rate and discovered a new miscompilation in LLVM." (Abstract)
- WHY: On a benchmark of 9 previously reported TurboFan bugs it found all 9 with no false positives (20 timeouts), and false positives were about 1% on larger sets (Sec. 8.1); but only 61% of extracted IRs were within the supported subset, so it is partial, and it found no new V8 bug (the new bug was in LLVM).
- PRIORITY: medium - shows partial JIT checking
- READ: Abstract, introduction, Sec. 3 examples (skimmed), Sec. 8 evaluation start; Sec. 10 discussion not read.

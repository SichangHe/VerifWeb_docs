# p4_prior_work_check (authored by agents)

Labels: [fact] = verbatim quote from the cited source; [inference] = my reasoning from quoted facts; [belief] = my judgment, not checked; [not found] = my searches did not find it (that is not proof it does not exist).
Method: primary PDFs/pages downloaded and text-extracted; quotes copied from that text. Searches run 2026-11-04.

## Summary

- VeRA, Crocus/VeriISLE, EventRacer, and V8's linear-time RegExp engine all exist. What each one verified is quoted below.
- I found no formal verification of the V8 TurboFan typer, no verification of TurboFan side-effect annotations, and no verification of Maglev [not found]. The closest work is TurboTV (ICSE 2024). It does translation validation of individual TurboFan compilations. It does not prove the typer sound.
- I found no published system matching "page-state snapshot as proof precondition + guard that invalidates the proof on state change" [not found]. The pieces exist separately:
  - JIT speculation with dependency invalidation (V8, SpiderMonkey TI); its formal version is CoreJIT, POPL 2021
  - staged static analysis that leaves residual runtime checks (Staged Information Flow, PLDI 2009; StaRVOOrS, RV 2015)
  - static analysis seeded with snapshots or single runs (HeapDL, OOPSLA 2017; Dynamic Determinacy, PLDI 2013)

## 1. VeRA: exists

Source: Brown, Renner, Nötzli, Lerner, Shacham, Stefan, "Towards a Verified Range Analysis for JavaScript JITs", PLDI 2020, https://doi.org/10.1145/3385412.3385968. PDF: https://par.nsf.gov/servlets/purl/10168655 (mirror: https://www.cs.utexas.edu/~hovav/dist/vera.pdf)

- [fact] "We present VeRA, a system for verifying the range analysis pass in browser just-in-time (JIT) compilers. Browser developers write range analysis routines in a subset of C++, and verification developers write infrastructure to verify custom analysis properties. Then, VeRA automatically verifies the range analysis routines, which browser developers can integrate directly into the JIT. We use VeRA to translate and verify Firefox range analysis routines, and it detects a new, confirmed bug that has existed in the browser for six years."
- [fact] method: "a Satisfiability Modulo Theories [36] (SMT)based verification tool that proves the correctness of these analyses with respect to JavaScript semantics."
- [fact] scope limits (§7): "We only verify range analysis routines for Firefox. Chrome's range analysis pass is tied to its type inference pass—different ranges correspond to different types (e.g., 32-bit integers have a bound). We consider extending VeRA to other browsers future work." Also: "We also do not verify the range analysis algorithm itself nor Firefox's use of ranges in code generation or other optimization passes (e.g., DCE or BCE)."
- [inference] What VeRA verified: the per-operator range-transfer routines of SpiderMonkey/IonMonkey (`Range` methods), checked against JS semantics. It did not verify the fixpoint algorithm, the code that consumes the ranges, or anything in V8.

## 2. Crocus / VeriISLE: exists (one line of work; VeriISLE is the in-tree tool, Crocus is the ASPLOS'24 name)

Source: VanHattum, Pardeshi, Fallin, Sampson, Brown, "Lightweight, Modular Verification for WebAssembly-to-Native Instruction Selection", ASPLOS 2024, https://doi.org/10.1145/3617232.3624862. Preprint: https://cs.wellesley.edu/~avh/veri-isle-preprint.pdf

- [fact] "In this paper, we present Crocus, a system for lightweight, modular verification of instruction-lowering rules within Cranelift, a production retargetable Wasm native code generator. We use Crocus to verify lowering rules that cover WebAssembly 1.0 support for integer operations in the ARM aarch64 backend. We show that Crocus can reproduce 3 known bugs (including a 9.9/10 severity CVE), identify 2 previously-unknown bugs and an underspecified compiler invariant, and help analyze the root causes of a new bug."
- [fact] Wasmtime README (https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/isle/veri/README.md): "VeriISLE is an in-development [SMT](https://smt-lib.org)-based verifier for the [ISLE language]" … "It analyzes chains of ISLE rules, using a combination of hand-written `spec`s and specifications derived from authoritative ISA semantics, such as [ASL] … for the `aarch64` backend."
- [fact] The same README names a follow-up paper: "The most recent OOPSLA 2025 paper described the automatic rule chaining, authoritative ISA specification derivations, and our current state modeling approach: [Scaling Instruction-Selection Verification against Authoritative ISA Semantics](https://doi.org/10.1145/3764383). Michael McLoughlin, Ashley Sheng, Chris Fallin, Bryan Parno, Fraser Brown, and Alexa VanHattum. OOPSLA 2025."
- [inference] What it verified: Cranelift's ISLE rewrite rules for lowering IR to aarch64, checked rule by rule with SMT. This is Wasm, not JS, and it covers only instruction selection.

## 3. EventRacer: exists (with its PLDI'12 predecessor WebRacer)

Predecessor: Petrov, Vechev, Sridharan, Dolby, "Race Detection for Web Applications", PLDI 2012, https://doi.org/10.1145/2254064.2254095. PDF: https://typeset.io/pdf/race-detection-for-web-applications-294zjgggzp.pdf
- [fact] "We present the first formulation of a happens-before relation for common web platform features." … "Based on the above, we implemented WEBRACER, the first dynamic race detector for web applications. WEBRACER is implemented atop the production-quality WebKit engine".

EventRacer: Raychev, Vechev, Sridharan, "Effective Race Detection for Event-Driven Programs", OOPSLA 2013, https://doi.org/10.1145/2509136.2509538. Abstract: https://research.ibm.com/publications/effective-race-detection-for-event-driven-programs
- [fact] "First, we introduce race coverage, a systematic method for exposing ad hoc synchronization and other (potentially harmful) races to the user, significantly reducing false positives. Second, we present an efficient connectivity algorithm for computing race coverage. The algorithm is based on chain decomposition and leverages the structure of event-driven programs to dramatically decrease the overhead of vector clocks. We implemented our techniques in a tool called EVENTRACER and evaluated it on a number of public web sites."
- [fact] code: https://github.com/mvechev/eventracer README: "A race detection tool for event driven applications." … "Obtain a ER_actionlog file by exploring a website with an instrumented browser (see https://github.com/eth-srl/webkit)".
- [inference] EventRacer verifies nothing in the proof sense. It is dynamic detection: it records one trace and checks it against a happens-before model. It is relevant here because its happens-before model is a candidate semantics for the event loop.

## 4. Linear-time regex in browsers: exists in V8, opt-in only

V8 blog: Martin Bidlingmaier, "An additional non-backtracking RegExp engine", 11 Jan 2021, https://v8.dev/blog/non-backtracking-regexp
- [fact] "Starting with v8.8, V8 ships with a new experimental non-backtracking RegExp engine (in addition to the existing Irregexp engine) which guarantees execution in linear time with respect to the size of the subject string. The experimental engine is available behind the feature flags mentioned below."
- [fact] "--enable-experimental-regexp_engine-on-excessive-backtracks enables the fallback to the non-backtracking engine on excessive backtracks." / "--regexp-backtracks-before-fallback N (default N = 50,000) specifies how many backtracks are considered "excessive", i.e. when the fallback kicks in."
- [fact] "For now it remains experimental because Irregexp is orders of magnitude faster than the new engine on most common patterns."
- [fact] RE2 lineage: "V8's new RegExp engine is based on this algorithm and its implementation in the re2 and Rust regex libraries."

Current default, from V8 main `src/flags/flag-definitions.h` (https://github.com/v8/v8/blob/main/src/flags/flag-definitions.h, fetched 2026-11-04):
- [fact] `DEFINE_BOOL(default_to_experimental_regexp_engine, false, "run regexps with the experimental engine where possible")`
- [fact] the fallback flag is declared with `DEFINE_EXPERIMENTAL_FEATURE(enable_experimental_regexp_engine_on_excessive_backtracks, "fall back to a breadth-first regexp engine on excessive " "backtracking")`, and that macro expands to `FLAG(BOOL, bool, nam, false, cmt " (experimental)")`, so its default is false.
- [inference] In V8's default configuration, matching is still done by the backtracking Irregexp engine. I did not check whether Chrome overrides these flags in the field (for example through Finch experiments) [not found].

Academic follow-up: Barrière, Pit-Claudel, "Linear Matching of JavaScript Regular Expressions", https://arxiv.org/abs/2311.17620
- [fact] "we discover several cases where state-of-the-art algorithms were either wrong (semantically incorrect), inefficient (suffering from superlinear complexity) or excessively restrictive" … "presenting the first nonbacktracking algorithms for matching lookarounds in linear time" … "some have also been merged in the V8 JavaScript implementation used in Chrome and Node.js."
- [belief] It appeared at PLDI 2024. I have not verified the venue.

Other browsers:
- [fact] SpiderMonkey imports V8's Irregexp. Mozilla Hacks, "A New RegExp Engine in SpiderMonkey" (2020), https://hacks.mozilla.org/2020/06/a-new-regexp-engine-in-spidermonkey/: "SpiderMonkey is using the very latest version of Irregexp, imported from the V8 repository"; "Irregexp has two strategies for executing RegExps: a bytecode interpreter, and a just-in-time compiler".
- [not found] Any shipped non-backtracking engine in SpiderMonkey or JavaScriptCore.

## 5. Verification of V8 TurboFan/Maglev typer or side-effect analysis

[not found] Any proof that the TurboFan Typer/OperationTyper is sound. [not found] Any verification of TurboFan's operator properties or effect annotations (e.g., `kNoWrite`). [not found] Any formal work on Maglev. Searches found only fuzzers (FuzzJIT, JIT-Picking, OptFuzz, DUMPLING, Artemis) and exploit write-ups.

Closest work: TurboTV. Kwon, Kwon, Kang, Lee, Heo, "Translation Validation for JIT Compiler in the V8 JavaScript Engine", ICSE 2024, https://doi.org/10.1145/3597503.3639189. PDF: https://prosys.kaist.ac.kr/publications/icse24.pdf
- [fact] "We present TurboTV, a translation validator for the JavaScript (JS) just-in-time (JIT) compiler of V8." … "We tackle this problem with an SMT-based translation validation (TV) that checks whether a specific compilation is semantically correct. We formally define the semantics of IR of TurboFan (JIT compiler of V8) as SMT encoding."
- [fact] scope: "The goal of TurboTV is to validate intraprocedural optimizations of loop-free functions." / "TurboTV only supports loop-free functions."
- [fact] effects: "we only need to prove the validity of the effect edges that represent dependencies introduced by side-effects such as memory load and store."
- [fact] "We excluded other bugs reported before because V8 fundamentally changed the memory model in Dec 2019."
- [inference] TurboTV checks one compilation at a time. A typer bug shows up only as a reduction that fails validation; the typing rules themselves are never proved sound. TurboTV also validates the effect edges in a graph. It does not prove that per-operator side-effect annotations are correct for all inputs.

Neighboring work on SpiderMonkey (not V8): Icarus. Smith, Sharma, Renner, Thien, Brown, Shacham, Jhala, Stefan, "Icarus: Trustworthy Just-In-Time Compilers with Symbolic Meta-Execution", SOSP 2024, https://doi.org/10.1145/3694715.3695949. PDF: https://par.nsf.gov/servlets/purl/10545043
- [fact] "a novel technique called symbolic meta-execution that encodes the behaviors of all possible JIT-generated programs as a single Boogie meta-program which can be efficiently verified by SMT solvers. We evaluate Icarus by using it to re-implement components of Firefox's JavaScript JIT."
- [fact] "we port and verify 21 high-level IC stub generators, which output ops in SpiderMonkey's CacheIR intermediate representation."

## 6. Closest prior work: "page-state snapshot as precondition + guard that invalidates the proof on state change"

[not found] Any work that proves properties of page scripts under a captured page-state precondition and adds a runtime guard that withdraws the proof when that state changes.

[inference] The closest work, ranked by how many of the three ingredients it covers (proof, snapshot precondition, invalidating guard):

### 6a. JIT speculation with dependency-based invalidation: the same mechanism in industry, minus proofs
- V8 `src/compiler/compilation-dependencies.h` (https://github.com/v8/v8/blob/main/src/compiler/compilation-dependencies.h):
  - [fact] "// Collects and installs dependencies of the code that is being generated."
  - [fact] "// Record the assumption that {map} stays stable."
  - [fact] "// Depend on the fact that accessing property |property_name| from // |receiver_map| yields the constant value |constant|, which is held by // |holder|. Therefore, must be invalidated if |property_name| is added to any // of the objects between receiver and |holder| on the prototype chain, b) any // of the objects on the prototype chain up to |holder| change prototypes, or // c) the value of |property_name| in |holder| changes."
- SpiderMonkey hybrid type inference. Hackett & Guo, "Fast and Precise Hybrid Type Inference for JavaScript", PLDI 2012, https://doi.org/10.1145/2254064.2254094. Abstract via https://www.sciweavers.org/node/339172:
  - [fact] "we present a hybrid type inference algorithm for JavaScript based on points-to analysis" … "by augmenting static analysis with run-time type barriers."
  - [fact] Mozilla wiki (https://wiki.mozilla.org/TypeInference): "If assumptions about type information are broken, the analysis is re-run on anything depending on that information. This can cause methods to be recompiled, even replacing currently running methods on the stack."
- [inference] In both engines, facts about the current heap act as a precondition, a guard checks them at run time, and a broken guard invalidates whatever depended on them. What is missing compared with the target: the facts serve optimization, they are not machine-checked proofs, and they concern engine internals (maps, type sets), not app-level properties.

### 6b. A formally verified version of 6a
Barrière, Blazy, Flückiger, Pichardie, Vitek, "Formally Verified Speculation and Deoptimization in a JIT Compiler", POPL 2021, https://doi.org/10.1145/3434327. PDF: https://aurele-barriere.github.io/papers/corejit.pdf
- [fact] "Just-in-time compilers for dynamic languages routinely generate code under assumptions that may be invalidated at run-time" … "This paper presents a model just-in-time compiler with an intermediate representation that explicits the synchronization points used for deoptimization and the assumptions made by the compiler's speculation." … "The optimizations are proved correct with the help of a proof assistant. While our work stops short of proving native code generation".
- [inference] This is the closest formal template: correctness under an assumption, plus a proved-correct fallback when the assumption fails. It is a model JIT, not a browser, and not a page-level property.

### 6c. Staged static analysis of web pages with residual checks (precondition = currently loaded code)
Chugh, Meister, Jhala, Lerner, "Staged Information Flow for JavaScript", PLDI 2009, https://doi.org/10.1145/1542476.1542483. Abstract via https://api.openalex.org/works/doi:10.1145/1542476.1542483
- [fact] "Our framework propagates information flow through the currently known code in order to compute a minimal set of syntactic residual checks that are performed on the remaining code when it is dynamically loaded." … "our technique allows the enforcement of information-flow policies with almost no run-time overhead."
- [inference] This is the closest web-specific match. The analysis assumes what is already loaded and checks new code when it arrives. Its precondition is code, not heap/DOM state. Its guards are syntactic checks on new code, not watches on state changes.

### 6d. Partial proof + runtime monitor for the rest
Ahrendt, Chimento, Pace, Schneider, "StaRVOOrS: A Tool for Combined Static and Runtime Verification of Java", RV 2015, https://doi.org/10.1007/978-3-319-23820-3_21. Abstract: https://www.cse.chalmers.se/~ahrendt/papers/RV15.abstract.txt
- [fact] "The tool automates a framework which uses partial results extracted from static verification to optimise the runtime monitoring process. StaRVOOrs combines the deductive theorem prover KeY and the RV tool LARVA".
- [inference] This matches "proof + guard", but in Java, and the precondition is a specification, not a captured snapshot.

### 6e. Snapshot- or single-run-seeded analysis (the precondition half, no guard)
- Grech, Fourtounis, Francalanza, Smaragdakis, "Heaps Don't Lie: Countering Unsoundness with Heap Snapshots", OOPSLA 2017, https://doi.org/10.1145/3133892. PDF: https://yanniss.github.io/heapdl-oopsla17.pdf
  - [fact] "consists in taking whole-heap snapshots during program execution, that are further enriched to capture significant aspects of dynamic behavior … The snapshots are then used as extra inputs to the static analysis." (Java/DaCapo, not JS)
- Schäfer, Sridharan, Dolby, Tip, "Dynamic Determinacy Analysis", PLDI 2013, https://doi.org/10.1145/2491956.2462168. Abstract via OpenAlex:
  - [fact] "Our analysis is completely dynamic and only needs to observe a single execution of the program, yet the determinacy facts it infers hold for any execution." … "a prototype implementation that handles full JavaScript."
- Leads I did not verify (search summaries only, no verbatim text checked):
  - Andreasen & Møller, "Determinacy in Static Analysis for jQuery", OOPSLA 2014, https://cs.au.dk/~amoeller/papers/jquery/paper.pdf
  - Prepack, a JS partial evaluator that runs initialization code and emits the resulting heap; archived; https://github.com/facebookarchive/prepack

### Gap statement
- [inference] No source above combines all three of: (i) machine-checked proofs (e.g., Verus) of page-script properties, (ii) a precondition taken from a live page/DOM/heap snapshot, (iii) a runtime guard tied to that precondition that invalidates the proof on mutation.
- [inference] The closest pairs:
  - 6a + 6b supply (iii) and a formal treatment of it
  - 6c supplies the web-page staging idea
  - 6e supplies (ii)
- [belief] The cheapest guard design to borrow is V8-style compilation dependencies (map stability, constant-field, and prototype-chain watchpoints). V8 already maintains these invalidation hooks.

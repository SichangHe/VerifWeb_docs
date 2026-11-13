# Independent review of prior-work claims
(authored by agents unless marked 🧑)

Reviewed `out/cloud/p4_prior_work_check.md`. Downloaded the cited sources independently into `prior_sources/`; did not execute code from them. “Confirmed” below means the cited source supports the claim, not that I reran its experiments or verified its proofs. Source text, including unsuccessful HTTP responses, is preserved there. This is a source audit, not an exhaustive literature search.

## Actionable findings

1. **Overstated: §2 collapses Crocus and current VeriISLE into “checked rule by rule.”** The cited current [VeriISLE README](https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/isle/veri/README.md) says: “It analyzes chains of ISLE rules, using a combination of hand-written `spec`s and specifications derived from authoritative ISA semantics”. Distinguish the ASPLOS 2024 evaluation from the later system. The README also says: “The most recent OOPSLA 2025 paper described the automatic rule chaining, authoritative ISA specification derivations, and our current state modeling approach”. The report quotes this correctly, then gives a narrower combined characterization.

2. **Overstated: §6e and the gap summary treat Dynamic Determinacy as supplying a snapshot precondition.** Its [abstract](https://api.openalex.org/works/doi:10.1145/2491956.2462168) says: “Our analysis is completely dynamic and only needs to observe a single execution of the program, yet the determinacy facts it infers hold for any execution.” It adds: “We present a formal soundness proof of the analysis for a simple imperative language, and a prototype implementation that handles full JavaScript.” Those are universal facts inferred from an execution, not facts valid only under a captured mutable-state precondition. It also has a formal proof, although the abstract does not establish machine checking. HeapDL likewise uses snapshots as additional analysis inputs; that is not itself a conditional proof of a specific page state. Describe these as sources of analysis information, not established implementations of ingredient (ii).

3. **Unverifiable: novelty and “closest” rankings.** The repeated “I found no…” statements are appropriately qualified search reports, but no query log, databases searched, or coverage bounds accompany them. I cannot reproduce an absence result for TurboFan typer proofs, effect annotations, Maglev, other browsers' non-backtracking engines, or the three-part proposed combination. The cited papers do not establish global absence or that TurboTV/CoreJIT/Staged Information Flow are uniquely closest. Retain the negative-search wording and qualify comparisons as “among these sources.”

4. **Unverifiable: “cheapest guard design.”** Existing V8 hooks are confirmed below; comparative engineering cost and coverage of DOM/application mutations are not measured. Dependency invalidation does not establish that all needed application facts can be watched. Keep this a proposed design, not an established differentiator or feasibility result.

5. **Overstated if read as present-day Chrome behavior: “opt-in only.”** Current V8 source defaults are confirmed. The report itself says it did not check Chrome overrides. Scope the heading to V8 source defaults; the 2021 performance and feature-support statements describe that blog's date.

## Claim-by-claim source audit

### Summary and method

- **Confirmed:** VeRA, Crocus/VeriISLE, EventRacer, and V8's experimental linear-time engine exist; independent source retrieval succeeded.
- **Confirmed with limits:** TurboTV performs translation validation, not a general proof of the typer (details below).
- **Unverifiable:** the author's exact searches and search date. This review does not authenticate the original download or search history.
- **Confirmed:** the separately cited families exist: JIT invalidation, verified speculation, staged analysis, static/runtime verification, and execution-seeded analysis. **Overstated:** these facts alone establish a novelty gap; see findings 2–3.

### 1. VeRA

**Confirmed:** title, authors, PLDI 2020, existence, C++ subset, SMT method, Firefox target, six-year bug claim, and exclusions, as claims of the [paper](https://www.cs.utexas.edu/~hovav/dist/vera.pdf). Its abstract says: “We use VeRA to translate and verify Firefox range analysis routines, and it detects a new, confirmed bug that has existed in the browser for six years.” Its limitations say: “We only verify range analysis routines for Firefox” and “We also do not verify the range analysis algorithm itself nor Firefox’s use of ranges in code generation or other optimization passes (e.g., DCE or BCE).” These support the report's transfer-routine/fixpoint/consumer/V8 distinctions.

**Scope caveat:** “verified routines” does not mean every attempted obligation passed. The paper reports: “We successfully prove or refute 137 conditions out of a possible 159, for a success rate of ≈86%”. This does not contradict the existing wording, but must accompany any stronger claim of complete range-analysis verification. The report's long quotes match the retrieved source after PDF line wrapping and typography normalization.

### 2. Crocus / VeriISLE

**Confirmed:** paper metadata, Wasm integer lowering to aarch64, SMT modular instruction selection, and the reported bug findings. The [preprint](https://cs.wellesley.edu/~avh/veri-isle-preprint.pdf) says: “We use Crocus to verify lowering rules that cover WebAssembly 1.0 support for integer operations in the ARM aarch64 backend.” It reports “3 known bugs (including a 9.9/10 severity CVE)” and “2 previously-unknown bugs and an underspecified compiler invariant”.

**Confirmed:** the [in-tree README](https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/isle/veri/README.md) identifies VeriISLE as an “in-development” SMT verifier, and names both the 2024 and 2025 publications and their authors. This supports one continuing line of work. **Overstated:** extending the 2024 rule-by-rule characterization to current VeriISLE (finding 1). “This is Wasm, not JS” is supported for the paper's evaluation, not a claim that all uses of Cranelift must originate in Wasm.

### 3. WebRacer / EventRacer

**Confirmed:** EventRacer title, OOPSLA 2013 publication, authors, dynamic race detection, race coverage, chain decomposition, and public-site evaluation. The [IBM abstract](https://research.ibm.com/publications/effective-race-detection-for-event-driven-programs) says: “The algorithm is based on chain decomposition and leverages the structure of event-driven programs to dramatically decrease the overhead of vector clocks.” The [repository README](https://github.com/mvechev/eventracer) says: “A race detection tool for event driven applications.” It instructs: “Obtain a ER_actionlog file by exploring a website with an instrumented browser”. These support trace-based detection, rather than a universal application-correctness proof.

**Unverifiable in this audit:** the exact WebRacer PLDI 2012 quotation and “first” claims. The cited typeset.io PDF returned HTTP 403; an attempted ETH alternative returned 404. This is an access limitation, not evidence the report is wrong. **Unverifiable recommendation:** whether the happens-before model is adequate as the target project's event-loop semantics; the existence of a useful race model alone does not establish that.

### 4. Linear-time regular expressions

**Confirmed:** all four historical blog quotations, date and author. The [V8 blog](https://v8.dev/blog/non-backtracking-regexp) says: “The experimental engine is available behind the feature flags mentioned below.” It also says: “The fallback mechanism does not apply to all patterns.” Its linear bound is with respect to subject-string length; it is not a constant independent of the pattern. The cited flag spellings and 50,000 threshold are present in the historical article.

**Confirmed:** the [current flag definitions](https://github.com/v8/v8/blob/main/src/flags/flag-definitions.h) contain `DEFINE_BOOL(default_to_experimental_regexp_engine, false,` and define the excessive-backtracking fallback with `DEFINE_EXPERIMENTAL_FEATURE`; that macro expands to `FLAG(BOOL, bool, nam, false, cmt " (experimental)")`. Ordinary V8 defaults therefore do not enable this engine/fallback. **Unverifiable:** Chrome field overrides; the report already acknowledges this limitation.

**Confirmed:** the [regular-expression paper abstract](https://arxiv.org/abs/2311.17620) reports incorrect, inefficient, or restrictive previous algorithms, new linear lookaround algorithms, and merges to V8. It says: “presenting the first nonbacktracking algorithms for matching lookarounds in linear time”. **Confirmed, strengthening the report's belief:** PLDI 2024 venue. [Crossref metadata](https://api.crossref.org/works/10.1145/3656431) lists `"issue":"PLDI"`, `"volume":"8"`, and publication date 2024-06-20 for *Linear Matching of JavaScript Regular Expressions*.

**Unverifiable in this audit:** Mozilla's exact 2020 quotations; its cited page returned HTTP 403 twice. **Unverifiable:** absence of shipped non-backtracking engines in SpiderMonkey/JavaScriptCore; no exhaustive current implementation audit was performed.

### 5. TurboFan / Maglev and Icarus

**Confirmed:** TurboTV metadata, translation-validation method, loop-free intraprocedural scope, effect-edge checking, and historical-memory-model quotation. The [paper](https://prosys.kaist.ac.kr/publications/icse24.pdf) states: “Given a JS function, TurboTV validates all the optimization steps (called reductions) during the JIT compilation.” It states: “The goal of TurboTV is to validate intraprocedural optimizations of loop-free functions.” Its effect validation section says: “we only need to prove the validity of the effect edges that represent dependencies introduced by side-effects such as memory load and store.” The December 2019 exclusion is present verbatim after PDF line-wrap normalization.

**Confirmed inference:** these are checks of particular IR transformations, not a universal soundness proof of typing rules or all per-operator effect annotations. **Overstated if interpreted as detection coverage:** “A typer bug shows up only as a reduction that fails validation” must not promise every typer bug is detected. This requires a supported compilation exhibiting a semantic violation; the paper's limitations still apply.

**Unverifiable:** all broad negative claims about typer/operator-property/Maglev verification and the claim that searches found “only” the listed fuzzers/exploit reports. The paper set does not prove these negatives.

**Confirmed:** Icarus authors/title/SOSP 2024 and quoted symbolic meta-execution / Firefox scope. The [paper](https://par.nsf.gov/servlets/purl/10545043) says: “Specifically, we port and verify 21 high-level IC stub generators, which output ops in SpiderMonkey’s CacheIR intermediate representation.” It also verifies a subset of CacheIR-to-MacroAssembler compilation; the report does not falsely claim to exhaust its contributions.

### 6. Snapshot preconditions and invalidation

**6a — confirmed:** the [V8 header](https://github.com/v8/v8/blob/main/src/compiler/compilation-dependencies.h) contains the quoted stable-map and prototype-chain dependency comments. For example: “Record the assumption that {map} stays stable.” It specifies invalidation when a property changes or relevant prototypes change. The [hybrid inference abstract](https://www.sciweavers.org/node/339172) contains “by augmenting static analysis with run-time type barriers.” The [Mozilla wiki](https://wiki.mozilla.org/TypeInference) says: “If assumptions about type information are broken, the analysis is re-run on anything depending on that information.” Thus assumptions plus invalidation/recompilation are supported. **Scope caveat:** not every dependency is an installed runtime guard: the same V8 header explicitly says slack tracking “gives no guarantees about slack tracking changes after the compilation is finished”. Limit the analogy to installed runtime dependencies. The claim that these sources themselves provide machine-checked app-property proofs is correctly rejected.

**6b — confirmed:** CoreJIT title/authors/POPL 2021, model JIT, speculative assumptions, proof-assisted optimization correctness, and omission of native code-generation proof. The [paper](https://aurele-barriere.github.io/papers/corejit.pdf) says: “The optimizations are proved correct with the help of a proof assistant. While our work stops short of proving native code generation”. A formal template for speculation/deoptimization is a supported comparison. **Unverifiable ranking:** “closest formal template.”

**6c — confirmed:** Staged Information Flow title/authors/PLDI 2009, currently-known-code analysis, residual checks on newly loaded code, and reported overhead. The [abstract](https://api.openalex.org/works/doi:10.1145/1542476.1542483) says: “Our framework propagates information flow through the currently known code in order to compute a minimal set of syntactic residual checks that are performed on the remaining code when it is dynamically loaded.” This supports the staging distinction. **Unverifiable from abstract alone:** exhaustive exclusion of heap-state preconditions and watches from the full system. An attempted full-paper retrieval failed. **Unverifiable ranking:** “closest web-specific match.”

**6d — confirmed:** StaRVOOrS author list, Java, KeY/LARVA combination and use of partial static results. The [authors' abstract](https://www.cse.chalmers.se/~ahrendt/papers/RV15.abstract.txt) says: “uses properties written using the ppDATE specification language which combines the control-flow property language DATE used in LARVA with Hoare triples assigned to states.” “Proof + guard” is a loose analogy to remaining runtime monitoring, not evidence of a snapshot-invalidation design. **Unverifiable from abstract alone:** the universal exclusion of captured-state preconditions.

**6e — confirmed:** HeapDL title/authors/OOPSLA 2017, heap snapshots, Java/DaCapo evaluation and extra static-analysis inputs. The [paper](https://yanniss.github.io/heapdl-oopsla17.pdf) says: “The snapshots are then used as extra inputs to the static analysis.” Dynamic Determinacy metadata, single-execution claim and JavaScript prototype are confirmed by its [abstract](https://api.openalex.org/works/doi:10.1145/2491956.2462168). **Overstated classification:** treating these inputs as the proposed snapshot proof precondition; see finding 2.

**Unverifiable, explicitly unverified in original:** jQuery determinacy and Prepack lead descriptions. These were not used as evidence for the conclusions.

**Gap statement — supported only as a bounded reading:** none of the confirmed descriptions establishes all three proposed ingredients together. **Unverifiable:** that none of the full systems does so, or that no other published work does so. The “closest pairs” are useful analogies, except assigning a conditional precondition to Dynamic Determinacy is misleading. Existing V8 dependency hooks are confirmed; cost and suitability for arbitrary page-state properties remain unverified.

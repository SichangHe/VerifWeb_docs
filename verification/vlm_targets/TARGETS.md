# Candidate verification targets for web/JavaScript
(authored by agents unless marked 🧑)

Answers two Nov 3 meeting actions (transcript /ssd1/sichangheagent/email/1103madhyastha_govindan_ghavidel.vtt; speaker labels unreliable):
- 🧑 L506: "Don't jump at one idea. Write down 10 different things that you might like to verify, either about individual JavaScripts or the engine itself."
- 🧑 L554-556: "Think about, if you had to work in this space, what are the… Possible questions? What are the… you know, the correctness issues that you would address, what are the tools you would use"

Evidence files: the quotes and URLs are in `src_engine.md`, `src_isolation.md`, `src_programs.md`, `src_components.md` (this directory). The sibling evidence base is /ssd1/sichangheagent/phd_labs/ara/research_projects/web_js_survey/js_breakage_evidence.md, and the Rust tool survey is `rust_verifiers.md` in the same directory. Each target below cites its failure by source file and item number. Labels:
- fact: quoted from a fetched source
- inference: my reasoning
- recall: from memory, not checked this session

Everything except the quotes is an agent proposal for the student to judge.

## Takeaways

- The real failures fall into four layers: the JIT/GC (targets 1-4), isolation (5-6), browser components in Rust (7-10), and individual scripts (11-13).
- The most bite-sized Verus targets with a crisp spec are 7 (URL parser vs. WHATWG) and 8 (HTML parse/serialize fixed point) (inference). Both are pure Rust in Servo's dependencies, each with an executable spec and an existing test suite (WPT).
- The highest-impact targets are 1-3 (JIT soundness) (inference). V8 accounted for 6 of 14 Chromium in-the-wild 0-days in 2021 (fact, `src_engine.md` stats 1). The space is crowded (fuzzing, VeRA-style range analysis verification, recall), so it needs a differentiator.
- The runtime-verification angle the meeting called possibly novel (L503) fits targets 1, 3, 6, 11 and 12 (inference): check the property on the concrete state at run time rather than proving it for all states.
- Target 6 (tab isolation inside one process) is the one the meeting raised directly (L474-481), and it has a cost argument. Process-per-site costs "a total memory overhead of 9-13%" (fact, Reis et al., `src_isolation.md`). Cloudflare: "the CPU cost can easily be 10x" (fact, same file).

## Targets

Each target lists the failure, the property, tools, a differentiator and a first step.

### 1. The JIT's side-effect model is sound
- Failure:
  - CVE-2020-6418 (V8, in the wild): "kJSCreate can have side-effects, for example by using a Proxy" (`src_engine.md` 1)
  - CVE-2019-11707 (SpiderMonkey, in the wild): "the JIT failed to ensure that calling Array.prototype.pop would not end up loading an array element from a prototype" (`src_engine.md` 6)
- Property: every IR node that may run user JS or write the heap invalidates the map/type facts inferred before it.
- Tools: Turbolizer IR dumps; an SMT/Verus model of the effect-chain analysis; Fuzzilli as a bug oracle.
- Differentiator (inference): Project Zero says these bugs "don't normally result in observable misbehaviour at runtime (i.e., a crash)" (fact, `src_engine.md` notes). A runtime monitor that re-checks inferred maps after every side-effecting node, in a debug build, would turn silent unsoundness into an observable failure. That's runtime verification where fuzzing is blind.
- First step: re-implement V8's map-inference function (`NodeProperties::InferMapsUnsafe`, recall) as a ~200-line Rust/Verus model and prove it marks results unreliable for every effectful opcode.

### 2. Typer ranges over-approximate runtime values
- Failure: CVE-2021-21220: "fool the V8 engine into thinking typer_index must be zero" (`src_engine.md` 5; root cause partly unverified)
- Property: for each opcode, the result range the typer computes contains every concrete result for inputs in the input ranges.
- Tools: SMT per opcode; prior work VeRA (Brown et al., verified range analysis for Firefox's JIT, recall: PLDI 2020).
- Differentiator (inference): VeRA covered SpiderMonkey. V8's Turbofan/Maglev typers are unverified as far as I know (unchecked). LLM agents could translate the C++ rules into checkable form.
- First step: encode the typer rules of 10 arithmetic opcodes in SMT and check soundness.

### 3. Compiler phases preserve cross-phase invariants
- Failure:
  - CVE-2021-4102: a later phase removed a node "after write-barrier elision was already decided" (`src_engine.md` 3)
  - CVE-2022-3723: a store path changed a field type "without deoptimizing any code that still relies on the previous FieldType" (`src_engine.md` 4)
- Property: a decision made in phase i (barrier elided, dependency registered) stays valid for the IR after phase j.
- Tools: translation validation per pass; V8's own heap verifier as a runtime check.
- Differentiator (inference): most verified-compiler work proves passes one at a time. These bugs are invariants that span passes.
- First step: state the write-barrier invariant as an IR predicate and check it after every Turbofan phase on the Fuzzilli corpus.

### 4. GC marking reaches its fixpoint before sweeping
- Failure: CVE-2021-37975 (V8, in the wild): "live objects may remain unmarked and be collected" (`src_engine.md` 2)
- Property: at sweep time every reachable object is marked, including ephemeron (WeakMap) values whose keys are live.
- Tools: a TLA+ or Verus model of the ephemeron loop; prior verified GCs (Iris, CakeML, recall).
- First step: model V8's ephemeron marking loop, reproduce the bug as a counterexample, then prove the fixed loop.

### 5. Sandboxed code accesses only its own memory
- Failure:
  - CVE-2023-26489 (Wasmtime): "a 35-bit effective address instead of WebAssembly's defined 33-bit" (`src_isolation.md` 2)
  - The V8 sandbox assumes an attacker "can read and write arbitrarily inside the V8 Sandbox" (`src_isolation.md` 5)
- Property: every load/store whose address the attacker influences lands inside its own cage or linear memory.
- Tools: VeriWasm; Cranelift ISLE-rule verification (recall: Crocus/VeriISLE); Verus.
- Differentiator (inference): Wasm-to-native has prior work. The V8 sandbox's pointer-table invariant (all pointers leaving the cage go through tables) seems unverified (unchecked).
- First step: state the V8 sandbox invariant for one external-pointer table and check it in a Verus model.

### 6. Tabs/tenants in one process cannot reach each other
- Failure:
  - vm2 CVE-2023-29017: "not properly handling host objects passed to `Error.prepareStackTrace`" (`src_isolation.md` 1)
  - Cloudflare: "isolates (which we use) also have bugs" (`src_isolation.md` 4)
  - Spook.js against Site Isolation (`src_isolation.md` 3)
- Meeting: 🧑 L474: "We cannot guarantee that we don't have bugs that would, for example, if we run two tabs in a single process."
- Property: no object reference from context A is reachable from context B except through declared channels. Speculative leaks (Spectre) are out of scope.
- Tools: V8 heap snapshots; Servo's per-realm design; Jalangi/NodeProf.
- Differentiator (inference): a runtime check of heap reachability between contexts, run on concrete heap states. This is the meeting's "for the given state" framing (L503) and is cheaper than proving the whole engine.
- First step: two V8 Contexts in one Isolate. Take a heap snapshot and compute whether B's object graph reaches anything in A. Replay vm2's escape to confirm the checker flags it.

### 7. The URL parser matches the WHATWG spec
- Failure:
  - Orange Tsai: "It's all about the inconsistency between URL parser and requester" (`src_components.md` 1)
  - rust-url #1130: a drive-letter rule applied to all schemes (`src_components.md` 2)
  - Lightpanda #1111 accepts `://foo.bar` (`src_components.md` 2)
- Property: for all strings s and bases b, `rust_url::parse(s, b)` equals the WHATWG basic URL parser; parse∘serialize round-trips.
- Tools: Verus on rust-url (used by Servo and Lightpanda); WPT `url/` tests as a check; spec extraction in the style of ESMeta (recall).
- Differentiator (inference): rust_verifiers.md reports no verified Servo component. This would be the first, with an unambiguous spec.
- First step: verify path normalization (`..`, drive letters) in Verus against a hand-transcribed spec of the WHATWG path state.

### 8. Sanitized HTML stays sanitized after parse/serialize
- Failure: DOMPurify CVE-2024-47875/45801: "nesting-based mXSS", "bypass the depth checking" (`src_components.md` 3)
- Property: `parse(serialize(t)) == t` for trees produced by the sanitizer, and the output has no script-capable nodes.
- Tools: html5ever (Servo); WPT/html5lib tests; Kani for bounded inputs.
- First step: use Kani to search for mutation-XSS trees on html5ever with a size bound.

### 9. The event loop drains microtasks in spec order
- Failure:
  - Lightpanda #1180: "Tasks executed in incorrect order" (`src_components.md` 6)
  - web event races (Petrov et al., PLDI 2012; quote not retrieved, `src_programs.md` 8)
- Property: after each task the microtask queue drains completely before the next task. A script's outcome doesn't depend on the order of unordered events (race-freedom).
- Tools: a state-machine model in Verus/TLA+; EventRacer (recall).
- First step: model the HTML event loop's task and microtask queues and check Servo's scheduler against it.

### 10. Servo's GC rooting contract holds in Drop and Trace
- Failure: Servo #24621 and #15318, use-after-free during the final GC from destructors touching GC objects (`src_components.md` 4). Servo's 2015 report calls the SpiderMonkey boundary "one of our largest areas of unsafe code" (rust_verifiers.md).
- Property: Drop of a DOM type touches no other GC object; every reachable GC pointer is rooted or traced.
- Tools: Servo's rooting lint (recall: "crown"); Miri; Kani.
- First step: write the contract as a checkable spec on `JSTraceable` and check derived impls on a few DOM types.

### 11. Built-in prototypes stay unchanged after library calls
- Failure: lodash CVE-2019-10744: "adding or modifying properties of Object.prototype using a constructor payload" (`src_programs.md` 5)
- Property: after any library call on untrusted input, built-in prototypes are unchanged.
- Tools: Jalangi/NodeProf runtime monitor; static taint tools.
- First step: a NodeProf monitor that snapshots `Object.prototype`, run over the test suites of the top 100 npm merge/clone utilities.

### 12. Third-party scripts never move sensitive data off-origin
- Failure:
  - polyfill.io: "a Chinese company bought the domain" (`src_programs.md` 2)
  - British Airways: card data sent "to a server hosted on baways.com" (`src_programs.md` 6)
  - event-stream payload (`src_programs.md` 3)
- Property: no script reads payment or credential fields and sends them to an origin outside an allowlist. The bytes of a third-party script match a pinned hash.
- Tools: information-flow monitors (JSFlow, FlowFox, recall); CSP/SRI; an instrumented crawl with Lightpanda or Playwright.
- Differentiator (inference): the group already has crawling infrastructure (meeting L439-447), so this could be measured on real sites.
- First step: crawl checkout pages and log which scripts read input fields and which origins they send to.

### 13. Regex matching takes linear time
- Failure: Cloudflare 2019: "a regular expression that backtracked enormously and exhausted CPU" (`src_programs.md` 1; the regex was PCRE, not JS, same bug class)
- Property: match time is linear in input length, or the regex is flagged.
- Tools: static ReDoS detectors; V8's experimental linear-time regexp engine (recall).
- First step: classify the regexes in the top npm packages as linear or super-linear.

Further candidates are in the sibling files, so I don't repeat them:
- js_breakage_evidence.md Part B: cross-engine differential checks, npm version drift, WebGL argument validation
- WEB_FAILURE_TARGETS.md: crawler-controller properties

## Possible questions, correctness issues and tools

This answers L554-556.

Questions a reviewer would ask (inference):
- Is the spec trustworthy? WHATWG/ECMA are executable specs, but the engine's internal invariants (targets 1-4) are undocumented.
- Does verifying a model say anything about the C++? Targets 1-4 verify models or re-implementations unless the work is in Rust (Servo).
- Static proof or runtime check? A proof covers every state, at high cost. A runtime check covers only the observed states, but runs on production code.
- Where do LLM agents help? Translating C++ rules or spec prose into checkable specs (targets 2, 7) is the plausible place (inference). Verus gives no counterexamples (verus_open_questions.md), which limits feedback to agents.

Correctness issues, by layer:
- JIT/GC: soundness of the analysis, cross-phase invariants, GC completeness
- isolation: memory confinement, reachability between contexts
- components: conformance to a parser spec, round-tripping, event ordering, unsafe contracts
- scripts: integrity of prototypes, data flow, resource bounds

Tools:
- Rust verifiers: Verus, Kani, Creusot (see rust_verifiers.md)
- SMT
- TLA+
- dynamic instrumentation: Jalangi, NodeProf
- fuzzing as a bug oracle: Fuzzilli
- WPT and Test262 as test oracles
- Servo and Lightpanda as substrates

## Gaps

- No JavaScriptCore case, no universal-XSS case, no specific CVE for a V8 sandbox bypass (searches were blocked or found nothing).
- The Ocariza and Petrov study quotes were not retrieved.
- The prior-work items marked "recall" (VeRA, Crocus/VeriISLE, crown, EventRacer, linear-time regexp) were not checked this session. The cloud survey tasks in CLOUD_HANDOFF.md should confirm them.

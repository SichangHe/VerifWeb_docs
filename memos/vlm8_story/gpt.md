(authored by agents unless marked 🧑)

> “What is the story? It needs to be a coherent story to be something I do for my PhD.”

I see three defensible stories. #1 has the best evidence today; #2 has the clearest novel thesis but highest risk; #3 is the cleanest traditional systems-verification story.

### 1. verified JavaScript builtins: from language standard to running engine

- thesis: build a pipeline that turns ECMA-262 algorithms into machine-checked specifications for Rust JavaScript engines, proving implementations and finding semantic bugs beyond test262
- problem: JS engines repeatedly approximate mathematical/spec operations with machine integers, cached lengths, and mutable state; tests sample inputs, so boundary and callback-induced bugs survive
- new vs prior work: VeRA verifies Firefox range-analysis routines, but explicitly says, “We also do not verify the range analysis algorithm itself nor Firefox's use of ranges” (Brown et al., PLDI 2020, §7); the reviewed search found no ECMA-262-builtins → Verus → Rust-engine pipeline
- support: the String.prototype.at proof exposed a real Boa crash; independent review confirmed it and a wrong Array.prototype.at result; related Boa/Nova work found multiple spec bugs around integer conversion and resizable buffers
- support: the bug-mutant experiment killed 4/4 selected modeled bugs, while the Blob survivor and proof audit show why specification strength must itself be measured
- missing: specs are still hand-transcribed; proofs are ports rather than Boa source; proxies/getters/object semantics are mostly absent; no large held-out evaluation
- next: mechanically derive one family of specs from ESMeta; verify a coherent builtin family such as indexing/conversion directly or through a mechanically checked extraction; freeze specs and evaluate on held-out historical/current bug-fix pairs plus test262
- biggest risk: connecting ECMA-262 semantics to production Rust may consume the thesis; without a reusable methodology, this degenerates into “find engine bugs with Verus”

### 2. proofs for the current page, with guards and re-verification

- thesis: prove security properties of JavaScript conditional on the page state observed now, track exactly which state the proof depends on, and invalidate/reverify when those assumptions change
- problem: “for every possible page state” is often intractable, while runtime monitoring only tells you about one execution; browsers already live in the middle, constantly specializing to current state
- new vs prior work: CoreJIT formalizes JIT code built under assumptions “that may be invalidated at run-time” (Barrière et al., POPL 2021), while staged information flow propagates through “currently known code” and leaves “residual checks” (Chugh et al., PLDI 2009); the reviewed search found no page-state snapshot + machine proof + invalidating guard system
- support: the real-page experiments show exactly the dynamic environment this targets—prototype changes, third-party flows, changing scripts—and browser JIT dependency invalidation provides an existence proof for the guard mechanism
- missing: almost everything central—the current symbolic executor is unsound, there is no guard, no dependency extraction theorem, no fallback/reverification, and no real-script proof
- next: choose one narrow property such as “this script cannot read cookie”; build a sound small-JS semantics producing both proof and dependency set; implement guarded invalidation in Boa/browser instrumentation and measure guard lifetime/overhead on captured pages
- biggest risk: either the useful dependency set changes constantly, making proofs worthless, or supporting enough JavaScript/browser semantics makes the project intractable; novelty is plausible, not established

### 3. verify the assumptions that make JavaScript JIT optimization safe

- thesis: verify JIT analysis facts—numeric ranges, side-effect summaries, and cross-phase invariants—once at their source, so every optimization relying on them inherits a checked assumption
- problem: several serious JIT failures arise because an optimizer believes a fact that is false or later invalidated; validating only final compilations catches symptoms rather than proving the analysis producing those facts
- new vs prior work: TurboTV says it checks whether “a specific compilation is semantically correct” and is limited to “loop-free functions” (Kwon et al., ICSE 2024); VeRA covers Firefox transfer routines but not their consumers; the reviewed search found no V8 TurboFan typer/effect-annotation verification
- support: the bounded side-effect model reproduces the CVE-2020-6418 failure shape and rejects the historical buggy variant; 9/10 modeled integer typer rules passed; the cross-phase Verus example shows the relevant proof form
- missing: these are hand-written models, not V8; floats/NaN/−0 are missing; the typer fixpoint and optimization consumers are unverified; bounded sequence checking is not a proof
- next: extract one small real V8 table/subsystem such as operator effects or integer OperationTyper; verify it against explicit JS semantics and historical fixes; then verify one downstream optimization that consumes those facts
- biggest risk: V8's C++ representation and JS numeric semantics make implementation correspondence expensive, while VeRA/TurboTV/Icarus leave less conceptual whitespace than story #2

My current ordering would be **#1 > #2 > #3**. #1 already has the beginning of a research loop—standard → specification → proof → previously missed production bug → independent confirmation—and can absorb proof-strength testing and proof maintenance later. #2 is the more distinctive PhD idea, but today it is a research hypothesis rather than an achieved result. #3 is credible, but the differentiator must be stated very sharply to avoid looking like “VeRA/TurboTV, but for another V8 component.”

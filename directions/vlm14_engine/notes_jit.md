# notes: verified js jit + explicit-effect core, evidence

(authored by agents unless marked 🧑)

notes
- local copies of papers read: out/vlm14_engine/pdf/*.txt (pdftotext). "[local]" = quote read from those by me. "[search-relayed]" = quoted by the web-search/fetch tool, not read by me; recheck. "[I]" = my inference.
- not found: team sizes of V8/SpiderMonkey/JSC; any Haskell-written JS engine benchmark; any verified full JS engine/JIT. sizes of engines: reuse out/vlm11_jsengine/sizes.md (not redone).
- nothing published or filed.

## 1. verified JITs and compilers

- icarus (SOSP 2024), https://www.cs.utexas.edu/~hovav/dist/icarus.pdf [local]
  - scope: verifies spidermonkey's CacheIR inline-cache stub generators only, not the whole jit.
  - "yields C++ code that is as fast as hand-written code"
  - "quickly detect real-world JIT bugs (<30 seconds) and verify fixed versions (in under a minute), and yield C++ code which, when integrated back into Firefox, passes all regression tests with no performance overhead"
  - fig 13: Octane 42,528 (stock) vs 42,527 (icarus); SunSpider 98 ms vs 97 ms. (table columns read from pdftotext layout; which column is stock is [I])
  - "We implement Icarus in roughly 20K SLOC of Rust"
  - tcb: "Icarus itself and the hand-written Boogie support code are both trusted components" (line wraps in pdftotext; treat as near-verbatim)
  - [I] verifies safety (no bad guard/OOB) of generated stubs, not full functional correctness of the optimizer; the speculation/deopt logic is untouched.
- jitk (OSDI 2014), https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-wang_xi.pdf [local]
  - bpf/seccomp only; "The JIT is written in Coq"; fig 16: 3,510 lines total, of which "Proof (SCPL, BPF) 2,300 lines of Coq", impl 520, spec 420.
  - no gc, no speculation: [I] tiny static translator.
- barriere et al. popl 2021 "Formally verified speculation and deoptimization in a JIT compiler", https://arxiv.org/abs/2012.00868 (hal pdf blocked by anti-bot; arxiv fetch returned another paper, so not read). 
  - from the popl 2023 text [local]: "Assume" instruction models speculation; "the semantics of the Assume instruction is defined in [Barrière et al. 2021]". model IR (not js), no native code in this paper. no perf numbers found.
- barriere, blazy, pichardie popl 2023, https://arxiv.org/pdf/2212.03129 [local]
  - abstract (tool-relayed): "a model JIT with dynamic generation of native code, implemented and formally verified in Coq"; proof method to "delimit, specify and reason on the impure effects of a JIT".
  - "The entire Coq development represents around 15K lines we wrote, and includes more than 160K lines from CompCert."
  - "On some programs, we observe up to 40 times speedups when dynamically compiling hot functions, compared to running our extracted interpreter alone."
  - "these speedups are only as good as the profiler and real programs may require better heuristics." no comparison to any real engine.
  - [I] relevance: closest existing design; effects handled by a "free interpreter" outside Coq (~1K OCaml) plus assumed behavior of primitives.
- vera (PLDI 2020? range-analysis verification in firefox jit): pdf url guessed wrongly; not read. vlm11 sizes.md already lists VeRA as "one JIT pass". not re-fetched.
- compcert, https://xavierleroy.org/publi/compcert-CACM.pdf [local]
  - "On average, CompCert code is only 7% slower than gcc -O1 and 12% slower than gcc -O2." (gcc 4.0.1, 2 GHz G5; "The test suite is too small to draw definitive conclusions")
  - "The whole Coq formalization and proof represents 42000" lines (cut by layout; 14% algorithms, 10% semantics, 76% correctness proofs).
  - [I] dated measurement (2009 era); modern gcc/llvm gap likely larger. not re-measured.
- cakeml backend (JFP 2019), https://kar.kent.ac.uk/71304/1/paper.pdf [local]
  - "For the small, purely functional benchmarks, our new compiler's performance is relatively close to the other compilers."
  - "there is clearly room for improvement on both small and large imperative benchmarks. ... we do not currently have any optimisations to remove bounds checks on arrays and vectors."
  - mlton "performs far better" on bignum (pidigits) because it uses GMP.
  - compared against mlton, ocaml, poly/ml, sml/nj; ratios only in figs 12/13 (not extracted). no single "x times slower than ocaml" number found.
- eBPF jits
  - jitterbug (OSDI 2020), https://www.usenix.org/system/files/osdi20-nelson.pdf [local]: "we found 16 new bugs in" (kernel jits, line cut); framework 1,825 lines Rosette; arm32 interp 1,265, x86 2,299; per-opcode verification time listed in seconds (rv64 mean 116, median 24, max 7,542 s [local fig 11, units assumed s]).
  - serval (SOSP 2019), https://unsat.cs.washington.edu/papers/nelson-serval.pdf [local]: "We find a total of 18 new bugs, all confirmed and fixed by developers."; contrasts certikos "roughly 10,000 lines of C and assembly ... 11 person-years, with a proof-to-implementation ratio of 20:1".
  - [I] push-button smt works because bpf programs are finite, loop-free, no heap; js is the opposite.
- wasm
  - vwasm (f*), https://github.com/secure-foundations/vWasm [search-relayed]: "A formally-verified provably-safe sandboxing Wasm-to-native compiler"; verifies sandboxing safety, not full semantic preservation [I from search text]; perf numbers not found by me.
  - wasmcert: "two mechanised specifications of the WebAssembly 1.0 semantics ... Isabelle ... Coq" https://conrad-watt.github.io/papers/watt2021.pdf [search-relayed]. spec only, not a fast engine.
  - crocus/veriisle (ASPLOS 2024), https://cs.wellesley.edu/~avh/veri-isle-preprint.pdf [search-relayed]: reproduces 3 known bugs, 2 new bugs; verifies cranelift instruction-selection rules, not the whole compiler.
  - arrival, https://cs.wellesley.edu/~avh/scaling-isa-preprint.pdf [search-relayed]: "Crocus in fact missed this bug" (sdiv trap); chains rules against authoritative isa semantics.
  - wasmtime issue 14957: "rule verifier unsoundness bug" https://github.com/bytecodealliance/wasmtime/issues/14957 [search-relayed]: even the verifier has bugs.
  - [I] pattern: successful verification targets are narrow layers (isel rules, ic stub generators, bpf), each with a finite/structured input space, and mostly find bugs rather than produce a verified whole.

## 2. js semantics and why jits are hard

- jscert (POPL 2014), https://www.doc.ic.ac.uk/~maffeis/papers/popl14.pdf [search-relayed]: "We present JSCert, a formalisation of the current ECMA standard in the Coq proof assistant, and JSRef, a reference interpreter for JavaScript extracted from Coq to OCaml." es5 only.
- kjs (PLDI 2015), https://dl.acm.org/doi/10.1145/2737924.2737991 [search-relayed]: "passes all 2,782 core language tests"; found bugs in v8, webkit, spidermonkey.
- jiset (ASE 2020), https://plrg.korea.ac.kr/assets/data/publication/ase20-park-jiset.pdf [search-relayed]: es10, "passed all 18,064 applicable tests in Test262" (tool wording). esmeta successor (arxiv 2204.14226) downloaded; I did not extract its numbers.
- none of these model a jit, ics, or gc; all are interpreters-of-the-spec [I]. vlm11 REPORT.md already states this.
- why jits are hard (evidence)
  - icarus intro [local]: "Unfortunately, this speed comes at the cost of security." and "Both Firefox and Chrome fell to JavaScript engine bugs at the Pwn2Own contest in March 2024." (wrapped lines)
  - barriere 2023 [local]: jits "greatly rely on a precise interplay between the different languages being executed, including on-stack-replacement" and are "scarcely formalized ... partly due to their impure nature".
  - [I] extra obligations a js jit needs beyond cakeml/compcert: speculation + deopt state reconstruction, shape/ic invariants, gc maps/write barriers, self-modifying code, concurrent compile threads. only the first has a mechanized treatment (barriere) and only on a toy IR.

## 3. engine size / team

- see out/vlm11_jsengine/sizes.md and REPORT.md (boa ~167k rust loc, nova ~117k, quickjs ~77k core c; verified systems 10-30x smaller; seL4 8.7k c / 200k proof / ~20 py).
- v8 (openhub, stale): "72,019 commits made by 912 contributors representing 2,307,245 lines of code" https://openhub.net/p/v8-js [search-relayed]; openhub says last tracked commit ~5 years ago.
- v8 team headcount, spiderMonkey team, jsc team: not found.
- [I] sota speed = several jit tiers + gc + tuned runtime ; vs boa/nova which are interpreters.

## 4. explicit effects / monadic core

- cakeml monadic translator (JAR 2020), https://link.springer.com/article/10.1007/s10817-020-09559-8 [search-relayed]: supports "references, exceptions, I/O, ... encapsulation of locally stateful computations inside pure functions"; earlier one (jfp14, https://cakeml.org/jfp14.pdf) handled "state-and-exception monad", case study hol light kernel. earlier code was "pure CakeML code that exposes the monadic plumbing in an explicit state-passing style" (ijcar18 motivation, tool wording).
  - [I] monads are used as a proof-friendly source; the translator erases them to real refs. runtime cost lands on the backend, not the monad.
- seL4 [search-relayed]: "We formalise the nondeterministic state monad with exceptions and failure in Isabelle/HOL." https://trustworthy.systems/publications/nicta_full_text/483.pdf ; haskell prototype auto-translated: "executable Isabelle/HOL specification" https://sel4.systems/Research/pdfs/comprehensive-formal-verification-os-microkernel.pdf . the monad is in the spec, not the shipped c code (c is refined to it) [I].
- interaction trees (POPL 2020), https://arxiv.org/abs/1906.00046 [search-relayed]: "A coinductive variant of 'free monads,' ITrees are built out of uninterpreted events and their continuations." compiler-correctness case study (imp to assembly-like). no perf claim; "work well with Coq's extraction" (tool wording). used in vellvm etc. (from memory only, unverified).
- lean 4 do + perceus
  - 'do' unchained https://lean-lang.org/papers/do.pdf [search-relayed]: local mutation, early return, iteration compiled to "purely functional code"; translation "formally prove[n] correct".
  - perceus (PLDI 2021), https://xnning.github.io/papers/perceus.pdf [local]: "on the tree insertion benchmark, the purely functional Koka implementation is within 10% of the performance of the in-place mutating algorithm in C++ (using std::map)"; "outstanding performance compared to these mature systems" (ocaml, haskell, swift, java). allocation-heavy benchmarks only; "we currently do not supply a cycle collector".
  - [I] caveat for js: js heaps are cyclic and graph-shaped (closures, prototypes, dom); rc + fbip needs a cycle collector; jit-generated code needs gc maps anyway.
- cogent (ASPLOS 2016 / arxiv 1601.05520), https://trustworthy.systems/publications/nicta_full_text/9425.pdf [local excerpt] : linear types give in-place updates from a functional language; bilbyfs/ext2. perf excerpt: "similar CPU usage at around 10%", "slightly slower than native ext2fs when performing random writes to a RAM disk. These slight performance overheads"... also "Occasionally, some overheads are introduced in C code generation". 
  - loc (thesis, search-relayed): ext2 4,077 c vs 2,789 cogent -> 12,066 generated c.
  - [I] works because file systems have tree/uniquely owned data and no gc; js doesn't.
- f* / low*: not searched (vWasm is f*, above).
- haskell-written engines/interpreters: no benchmark of a haskell js engine or jit found (one search). neil mitchell: "Compile to assembly or JIT - I didn't try this approach (it's a lot more work)" http://neilmitchell.blogspot.com/2020/04/writing-fast-interpreter.html [search-relayed]; his data is for a toy language.

## 5. evidence summary for the two questions (inference, not fact)

- sota perf + full verification: no precedent. closest: barriere 2023 (toy IR, 15k own lines + 160k compcert, 40x over its own interpreter), icarus (only IC stub generators, no perf loss).
- verified compilers pay a perf gap even in mature cases: compcert 7-12% behind gcc -O1/-O2 (2009-era measurement); cakeml "relatively close" on pure code, behind on imperative code.
- explicit effects/monads: strong evidence they help proofs (seL4, cakeml, itrees); evidence they cost nothing at runtime requires a compile step that erases them (cakeml translator, cogent, perceus); no evidence for js-scale jit.
- [I] a "monadic core" is a spec/proof-architecture choice, orthogonal to sota speed; the speed-critical parts (ics, tiering, gc, codegen) are the effectful ones and are where proofs are least developed.
